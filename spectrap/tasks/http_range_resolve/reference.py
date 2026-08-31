"""Reference implementation for CDN-2291 (HTTP byte-range resolution).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: RFC 7233 section 2.1 (byte ranges) and section 3.1 (an unsatisfiable
or unrecognised Range header field is ignored), plus the list rule of RFC 7230
section 7 for the comma-separated byte-range-set.

https://www.rfc-editor.org/rfc/rfc7233.html#section-2.1
"""

from __future__ import annotations

import re


class UnsatisfiableRange(Exception):
    """Every byte-range-spec was unsatisfiable (a 416, not a 400)."""


# byte-range-spec = first-byte-pos "-" [ last-byte-pos ]
# suffix-byte-range-spec = "-" suffix-length      (both are 1*DIGIT, RFC 7233 2.1)
#
# Two details that a shorter pattern gets wrong, both found by the independent
# crosscheck oracle rather than by inspection:
#   * `[0-9]`, not `\d`.  Python's `\d` matches every Unicode decimal digit, so
#     `\d+` would accept Arabic-Indic numerals as a byte offset; RFC 5234's
#     core rule is DIGIT = %x30-39.
#   * `\Z`, not `$`.  Python's `$` also matches immediately before a single
#     trailing newline, which would make a spec ending in LF valid.  RFC 7230
#     section 3.2.3 defines OWS = *( SP / HTAB ); LF is not optional whitespace.
_SPEC = re.compile(r"^(?:([0-9]+)-([0-9]*)|-([0-9]+))\Z")

# Parsed spec: (first, last, suffix); exactly one of first/suffix is not None,
# and last is None for an open-ended "first-" spec.
_Spec = tuple[int | None, int | None, int | None]


def _parse(header: str) -> list[_Spec] | None:
    """Parse a byte-ranges-specifier, or return None if it is malformed."""
    unit, sep, rest = header.strip(" \t").partition("=")
    # RFC 7233 3.1: a range unit we do not understand means "ignore the field".
    if not sep or unit.lower() != "bytes":
        return None

    specs: list[_Spec] = []
    for element in rest.split(","):
        element = element.strip(" \t")
        if not element:
            continue  # RFC 7230 section 7: empty list elements are legal and skipped
        match = _SPEC.match(element)
        if match is None:
            return None
        first_text, last_text, suffix_text = match.group(1), match.group(2), match.group(3)
        if suffix_text is not None:
            specs.append((None, None, int(suffix_text)))
            continue
        first = int(first_text)
        last = int(last_text) if last_text else None
        # RFC 7233 2.1: "A byte-range-spec is invalid if the last-byte-pos
        # value is present and less than the first-byte-pos."
        if last is not None and last < first:
            return None
        specs.append((first, last, None))

    return specs or None  # "bytes=" carries no spec at all, so it is malformed


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """Resolve a Range header value into inclusive (first, last) byte offsets."""
    if not isinstance(header, str):
        raise ValueError(f"header must be a str, got {type(header).__name__}")
    if not isinstance(length, int):
        raise ValueError(f"length must be an int, got {type(length).__name__}")
    if length < 0:
        raise ValueError(f"length must not be negative, got {length}")
    if length == 0:
        # No bytes exist, so nothing is servable and there is no whole object
        # to fall back to for an ignored header either.
        raise UnsatisfiableRange("representation is empty")

    specs = _parse(header)
    if specs is None:
        return [(0, length - 1)]  # ignored header => serve the whole thing

    resolved: list[tuple[int, int]] = []
    for first, last, suffix in specs:
        if suffix is not None:
            if suffix == 0:
                continue  # "bytes=-0": the last zero bytes are unsatisfiable
            # A suffix at or beyond the length yields the whole representation.
            resolved.append((max(0, length - suffix), length - 1))
            continue
        if first is None or first >= length:
            continue  # first-byte-pos past the end: unsatisfiable
        # RFC 7233 2.1: a last-byte-pos >= length is taken to be length - 1.
        resolved.append((first, length - 1 if last is None else min(last, length - 1)))

    if not resolved:
        raise UnsatisfiableRange(f"no satisfiable range in {header!r} for length {length}")
    return resolved
