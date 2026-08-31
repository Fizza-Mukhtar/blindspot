import re


class UnsatisfiableRange(Exception):
    """Raised when every byte-range in an otherwise well-formed header is
    unsatisfiable for the given representation length.

    Deliberately does not subclass ValueError: ValueError from this module
    means "could not parse the request" (-> 400), while this exception means
    "parsed fine, but none of it can be served" (-> 416).
    """


_RANGE_SPEC_RE = re.compile(r'^(\d+)-(\d+)$')
_OPEN_SPEC_RE = re.compile(r'^(\d+)-$')
_SUFFIX_SPEC_RE = re.compile(r'^-(\d+)$')


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """Resolve an HTTP ``Range`` header value into concrete byte offsets.

    Implements RFC 7233 section 2.1: ``header`` is the raw field value
    (e.g. ``\"bytes=0-499\"``) and ``length`` is the current length in bytes
    of the representation being served. Returns one inclusive ``(first,
    last)`` pair per requested range, in header order, with unsatisfiable
    specs silently dropped.

    Raises ``ValueError`` if the arguments themselves are invalid, and
    ``UnsatisfiableRange`` if every requested range is unsatisfiable (which
    is always the case when ``length`` is 0). A header whose syntax we do
    not understand, or whose elements are individually malformed, is
    ignored entirely and the whole representation is returned instead.
    """
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if isinstance(length, bool) or not isinstance(length, int):
        raise ValueError("length must be an int")
    if length < 0:
        raise ValueError("length must be zero or greater")

    if length == 0:
        raise UnsatisfiableRange(
            "a zero-length representation has no bytes to serve"
        )

    whole = [(0, length - 1)]

    stripped = header.strip(" \t")
    unit, sep, rest = stripped.partition("=")
    if not sep or unit.lower() != "bytes":
        return whole
    if rest[:1] in (" ", "\t"):
        return whole

    specs: list[tuple] = []
    saw_element = False
    for raw_elem in rest.split(","):
        elem = raw_elem.strip(" \t")
        if not elem:
            continue
        saw_element = True

        match = _RANGE_SPEC_RE.match(elem)
        if match:
            first, last = int(match.group(1)), int(match.group(2))
            if last < first:
                return whole
            specs.append(("range", first, last))
            continue

        match = _OPEN_SPEC_RE.match(elem)
        if match:
            specs.append(("open", int(match.group(1))))
            continue

        match = _SUFFIX_SPEC_RE.match(elem)
        if match:
            specs.append(("suffix", int(match.group(1))))
            continue

        return whole

    if not saw_element:
        return whole

    resolved: list[tuple[int, int]] = []
    for kind, *vals in specs:
        if kind == "range":
            first, last = vals
            if first >= length:
                continue
            resolved.append((first, min(last, length - 1)))
        elif kind == "open":
            (first,) = vals
            if first >= length:
                continue
            resolved.append((first, length - 1))
        else:  # suffix
            (suffix,) = vals
            if suffix == 0:
                continue
            start = max(0, length - suffix)
            resolved.append((start, length - 1))

    if not resolved:
        raise UnsatisfiableRange(
            "no requested range is satisfiable for this length"
        )

    return resolved
