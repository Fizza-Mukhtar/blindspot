"""Semantic Versioning 2.0.0 precedence sorting for release tags."""

import re

_VERSION_RE = re.compile(
    r"""
    ^
    v?
    (?P<major>0|[1-9]\d*)
    \.
    (?P<minor>0|[1-9]\d*)
    \.
    (?P<patch>0|[1-9]\d*)
    (?:-(?P<prerelease>[0-9A-Za-z.-]+))?
    (?:\+(?P<build>[0-9A-Za-z.-]+))?
    $
    """,
    re.VERBOSE,
)

_IDENTIFIER_RE = re.compile(r"^[0-9A-Za-z-]+$")
_NUMERIC_RE = re.compile(r"^(0|[1-9]\d*)$")


def _split_identifiers(raw: str, tag: str) -> tuple[str, ...]:
    """Split a dot-separated identifier list, rejecting empty or malformed parts."""
    identifiers = raw.split(".")
    for identifier in identifiers:
        if not identifier or not _IDENTIFIER_RE.match(identifier):
            raise ValueError(f"invalid version tag: {tag!r}")
    return tuple(identifiers)


def _prerelease_key(identifiers: tuple[str, ...], tag: str) -> tuple:
    """Build a per-identifier comparison key honoring numeric-vs-lexical rules."""
    key: list[tuple[int, object]] = []
    for identifier in identifiers:
        if _NUMERIC_RE.match(identifier):
            key.append((0, int(identifier)))
        elif identifier.isdigit():
            # All digits but rejected by _NUMERIC_RE means it carries a leading zero.
            raise ValueError(f"invalid version tag: {tag!r}")
        else:
            key.append((1, identifier))
    return tuple(key)


def _version_key(tag: str) -> tuple:
    """Compute a sortable precedence key for a single tag, per SemVer 2.0.0."""
    match = _VERSION_RE.match(tag)
    if not match:
        raise ValueError(f"invalid version tag: {tag!r}")

    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))

    prerelease_raw = match.group("prerelease")
    if prerelease_raw is not None:
        identifiers = _split_identifiers(prerelease_raw, tag)
        has_no_prerelease = 0
        prerelease_key = _prerelease_key(identifiers, tag)
    else:
        has_no_prerelease = 1
        prerelease_key = ()

    build_raw = match.group("build")
    if build_raw is not None:
        # Build metadata must be well-formed but never affects precedence.
        _split_identifiers(build_raw, tag)

    return (major, minor, patch, has_no_prerelease, prerelease_key)


def sort_versions(tags: list[str]) -> list[str]:
    """Return a new list of tags ordered by SemVer 2.0.0 precedence, lowest to highest.

    The input list is left untouched. The sort is stable, so tags that carry
    equal precedence (for example, differing only in ignored build metadata)
    retain their relative order from the input. Each tag must match the
    accepted ``[v]MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`` format; a
    malformed tag raises ``ValueError`` naming the offending tag.
    """
    return sorted(tags, key=_version_key)
