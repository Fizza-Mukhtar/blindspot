"""Reference implementation for SCHED-207 (half-open booking coalescing).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: the half-open interval convention `[start, end)` as argued in
E. W. Dijkstra, EWD 831, "Why numbering should start at zero",
https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD831.html
"""

from __future__ import annotations

Booking = tuple[int, int]


def _checked_pair(entry: object) -> Booking:
    """Validate one raw row and return it as a plain ``(int, int)`` tuple."""
    if not isinstance(entry, (tuple, list)) or len(entry) != 2:
        raise ValueError(f"booking must be a two-element (start, end) pair: {entry!r}")

    start, end = entry
    if not isinstance(start, int) or not isinstance(end, int):
        raise ValueError(f"booking bounds must be whole minutes: {entry!r}")

    if start > end:
        # The only genuine defect in a row.  start == end is legal: under the
        # half-open convention it is the empty interval, i.e. a cancellation.
        raise ValueError(f"booking ends before it starts: ({start}, {end})")

    return (start, end)


def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Coalesce half-open ``[start, end)`` bookings into the room's busy blocks."""
    # Validate every row up front so a bad row late in the list is still
    # reported, whatever the merging does.
    pairs = [_checked_pair(entry) for entry in intervals]

    # EWD 831: [s, s) contains no minutes.  A cancellation occupies no time, so
    # it is dropped *before* merging -- it can neither surface in the output nor
    # act as a bridge between two blocks that are really separated by free time.
    busy = [(start, end) for start, end in pairs if start != end]

    # Rows arrive from the database in arbitrary order.
    busy.sort()

    merged: list[Booking] = []
    for start, end in busy:
        if merged and start <= merged[-1][1]:
            # `<=`, not `<`: with half-open intervals, `start == prev_end` means
            # the two stretches touch with no free minute between them, so they
            # are one busy block.  A strict `<` here would leave the phantom gap
            # that motivated the ticket.
            prev_start, prev_end = merged[-1]
            # max(): the incoming booking may be wholly nested in the block.
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return merged
