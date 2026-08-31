"""Resolve HTTP Range header values into concrete byte offsets (RFC 7233 section 2.1)."""

import re

_HEADER_RE = re.compile(r'^bytes=(.*)$', re.IGNORECASE)
_FIRST_LAST_RE = re.compile(r'^\d+-\d+$')
_FIRST_ONLY_RE = re.compile(r'^\d+-$')
_SUFFIX_RE = re.compile(r'^-\d+$')


class UnsatisfiableRange(Exception):
    """Raised when no requested range can be satisfied for the given length."""


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """Resolve a Range header value into a list of inclusive (first, last) byte offsets.

    Malformed headers are ignored and the whole representation is returned.
    If every requested range is unsatisfiable (or length is 0), UnsatisfiableRange
    is raised.
    """
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if not isinstance(length, int) or length < 0:
        raise ValueError("length must be a non-negative int")

    if length == 0:
        raise UnsatisfiableRange("representation has zero length")

    whole = [(0, length - 1)]

    stripped = header.strip(' \t')
    header_match = _HEADER_RE.match(stripped)
    if header_match is None:
        return whole

    range_set = header_match.group(1)
    elements = [part.strip(' \t') for part in range_set.split(',')]
    nonempty = [e for e in elements if e != '']
    if not nonempty:
        return whole

    specs = []
    for element in nonempty:
        if _FIRST_LAST_RE.match(element):
            first_str, last_str = element.split('-', 1)
            first, last = int(first_str), int(last_str)
            if last < first:
                return whole
            specs.append(('first_last', first, last))
        elif _FIRST_ONLY_RE.match(element):
            first = int(element[:-1])
            specs.append(('first_only', first, None))
        elif _SUFFIX_RE.match(element):
            suffix = int(element[1:])
            specs.append(('suffix', None, suffix))
        else:
            return whole

    resolved: list[tuple[int, int]] = []
    for kind, first, value in specs:
        if kind == 'first_last':
            if first >= length:
                continue
            last = value if value < length else length - 1
            resolved.append((first, last))
        elif kind == 'first_only':
            if first >= length:
                continue
            resolved.append((first, length - 1))
        else:  # suffix
            suffix = value
            if suffix == 0:
                continue
            start = length - suffix if suffix < length else 0
            resolved.append((start, length - 1))

    if not resolved:
        raise UnsatisfiableRange("no requested range is satisfiable")

    return resolved
