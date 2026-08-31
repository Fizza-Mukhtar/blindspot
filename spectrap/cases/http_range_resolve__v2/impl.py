"""Resolve HTTP Range header values into concrete byte offsets (RFC 7233 section 2.1)."""

import re


class UnsatisfiableRange(Exception):
    """Raised when every byte-range-spec in a Range header is unsatisfiable."""


_OWS = " \t"
_UNIT_RE = re.compile(r"(?i:bytes)=(.*)")
_RANGE_SPEC_RE = re.compile(r"(\d+)-(\d+)")
_OPEN_SPEC_RE = re.compile(r"(\d+)-")
_SUFFIX_SPEC_RE = re.compile(r"-(\d+)")


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """Resolve a Range header value into concrete inclusive (first, last) byte offsets.

    Malformed headers are ignored and the whole representation is returned.
    Specs that cannot be satisfied are dropped, unless none of them can be,
    in which case UnsatisfiableRange is raised.
    """
    _validate_arguments(header, length)

    if length == 0:
        raise UnsatisfiableRange("empty representation has no bytes to serve")

    specs = _parse_range_specs(header)
    if specs is None:
        return [(0, length - 1)]

    resolved = [pair for pair in (_resolve_spec(spec, length) for spec in specs) if pair is not None]
    if not resolved:
        raise UnsatisfiableRange("no byte-range-spec in the header is satisfiable")
    return resolved


def _validate_arguments(header: str, length: int) -> None:
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if not isinstance(length, int) or length < 0:
        raise ValueError("length must be a non-negative int")


def _parse_range_specs(header: str) -> list[tuple] | None:
    """Parse the header into raw specs, or None if the header's syntax is invalid."""
    trimmed = header.strip(_OWS)
    match = _UNIT_RE.fullmatch(trimmed)
    if match is None:
        return None

    elements = [element.strip(_OWS) for element in match.group(1).split(",")]
    non_empty_elements = [element for element in elements if element]
    if not non_empty_elements:
        return None

    specs = []
    for element in non_empty_elements:
        spec = _parse_one_spec(element)
        if spec is None:
            return None
        specs.append(spec)
    return specs


def _parse_one_spec(element: str) -> tuple | None:
    """Parse a single byte-range-spec, or return None if it is malformed or invalid."""
    match = _RANGE_SPEC_RE.fullmatch(element)
    if match is not None:
        first, last = int(match.group(1)), int(match.group(2))
        if last < first:
            return None
        return ("range", first, last)

    match = _OPEN_SPEC_RE.fullmatch(element)
    if match is not None:
        return ("open", int(match.group(1)))

    match = _SUFFIX_SPEC_RE.fullmatch(element)
    if match is not None:
        return ("suffix", int(match.group(1)))

    return None


def _resolve_spec(spec: tuple, length: int) -> tuple[int, int] | None:
    """Resolve one parsed spec into an inclusive (first, last) pair, or None if unsatisfiable."""
    kind = spec[0]

    if kind == "range":
        _, first, last = spec
        if first >= length:
            return None
        return (first, min(last, length - 1))

    if kind == "open":
        _, first = spec
        if first >= length:
            return None
        return (first, length - 1)

    _, suffix = spec  # kind == "suffix"
    if suffix == 0:
        return None
    if suffix >= length:
        return (0, length - 1)
    return (length - suffix, length - 1)
