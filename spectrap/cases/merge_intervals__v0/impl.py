def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Coalesce raw room-booking rows into disjoint, non-touching busy blocks.

    Bookings use the half-open convention ``[start, end)``. Zero-length
    entries (``start == end``) represent cancelled reservations and are
    dropped before merging. Touching intervals (where one ends exactly where
    another begins) are merged into a single contiguous block, since no free
    minute separates them.

    Raises ``ValueError`` if any entry is malformed (not a two-element tuple
    or list of ints) or has ``start > end``.
    """
    validated: list[tuple[int, int]] = []
    for entry in intervals:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise ValueError(f"invalid booking entry: {entry!r}")
        start, end = entry
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError(f"invalid booking entry: {entry!r}")
        if start > end:
            raise ValueError(
                f"invalid booking interval (start > end): ({start}, {end})"
            )
        validated.append((start, end))

    nonempty = [iv for iv in validated if iv[0] != iv[1]]
    if not nonempty:
        return []

    nonempty.sort(key=lambda iv: iv[0])

    merged: list[tuple[int, int]] = [nonempty[0]]
    for start, end in nonempty[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            if end > last_end:
                merged[-1] = (last_start, end)
        else:
            merged.append((start, end))

    return merged
