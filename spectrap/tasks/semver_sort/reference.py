"""Reference implementation for RELENG-412 (SemVer 2.0.0 tag ordering).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: https://semver.org/spec/v2.0.0.html items 9-11.
"""

from __future__ import annotations

import re

# Two anchoring details that are easy to get wrong and were both found by the
# independent crosscheck oracle rather than by review:
#
#   * `\Z`, not `$`.  Python's `$` also matches immediately before a single
#     trailing newline, so `"1.0.0\n"` -- a tag read from a line-oriented source
#     such as `git tag` piped through a file -- would validate and then sort
#     under a name that is not the name it was given.
#   * `[0-9]`, not `\d`.  Python's `\d` matches every Unicode decimal digit,
#     and `int()` accepts them, so `\d*` would let non-ASCII numerals through
#     into a version number.  The SemVer BNF defines its digits as 0-9.
_TAG = re.compile(
    r"""^
    v?
    (?P<major>0|[1-9][0-9]*)\.
    (?P<minor>0|[1-9][0-9]*)\.
    (?P<patch>0|[1-9][0-9]*)
    (?:-(?P<prerelease>
        (?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)
        (?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*
    ))?
    (?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?
    \Z""",
    re.X,
)

_NUMERIC = re.compile(r"^[0-9]+\Z")


def _identifier_key(identifier: str) -> tuple[int, int, str]:
    """Sort key for one pre-release identifier.

    Item 11.4.3: "Numeric identifiers always have lower precedence than
    non-numeric identifiers."  The leading 0/1 encodes that class ordering;
    numeric identifiers then compare by value and alphanumeric ones by ASCII.
    """
    if _NUMERIC.match(identifier):
        return (0, int(identifier), "")
    return (1, 0, identifier)


def precedence_key(tag: str) -> tuple:
    """Total-order key implementing SemVer precedence.

    Build metadata is deliberately absent from the key (item 10), which is what
    makes equal-precedence ties observable and the sort's stability testable.
    """
    match = _TAG.match(tag)
    if match is None:
        raise ValueError(f"not a valid semantic version tag: {tag}")

    core = (int(match["major"]), int(match["minor"]), int(match["patch"]))
    prerelease = match["prerelease"]

    if prerelease is None:
        # Item 11.3: a normal version outranks any pre-release of itself.
        return (core, 1, ())

    identifiers = tuple(_identifier_key(part) for part in prerelease.split("."))
    # Item 11.4.4: with all preceding identifiers equal, more fields wins.
    # Tuple comparison gives that for free once the shared prefix is equal.
    return (core, 0, identifiers)


def sort_versions(tags: list[str]) -> list[str]:
    """Order tags from lowest to highest SemVer precedence, stably."""
    for tag in tags:
        if not isinstance(tag, str):
            raise ValueError(f"not a valid semantic version tag: {tag!r}")
        precedence_key(tag)  # validate every tag before producing any output
    return sorted(tags, key=precedence_key)
