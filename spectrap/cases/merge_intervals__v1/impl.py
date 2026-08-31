def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Coalesce raw half-open booking intervals into a room's real busy blocks.

    Cancelled (zero-length) rows are dropped first. Remaining intervals are
    merged so that touching or overlapping bookings become a single block,
    per the half-open [start, end) convention.
    """
    validated: list[tuple[int, int]] = []
    for entry in intervals:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise ValueError(f"invalid booking entry: {entry!r}")
        start, end = entry
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
        ):
            raise ValueError(f"invalid booking entry: {entry!r}")
        if start > end:
            raise ValueError(f"invalid booking interval, start > end: ({start}, {end})")
        validated.append((start, end))

    nonempty = [(s, e) for s, e in validated if s != e]
    if not nonempty:
        return []

    nonempty.sort(key=lambda iv: iv[0])

    merged: list[tuple[int, int]] = [nonempty[0]]
    for start, end in nonempty[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged
