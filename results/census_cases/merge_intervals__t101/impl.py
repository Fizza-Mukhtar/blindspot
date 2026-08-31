def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Merge overlapping or adjacent booking intervals into a single sorted list.

    Takes booking intervals as half-open [start, end) tuples (start inclusive,
    end exclusive) and returns a list of merged intervals sorted by start time.
    Zero-width intervals (start == end) are dropped as cancelled bookings.
    """
    # Validate and filter entries
    validated = []
    for entry in intervals:
        # Check if it's a tuple or list with exactly 2 elements
        if not isinstance(entry, (tuple, list)):
            raise ValueError(f"Entry must be a tuple or list, got {type(entry).__name__}")

        if len(entry) != 2:
            raise ValueError(f"Entry must have exactly 2 elements, got {len(entry)}")

        start, end = entry

        # Check if both are ints (and not bool)
        if type(start) is not int or type(end) is not int:
            raise ValueError("Entry elements must be integers")

        # Check if start > end
        if start > end:
            raise ValueError(f"({start}, {end})")

        # Skip zero-width intervals (cancellations)
        if start < end:
            validated.append((start, end))

    # If no valid intervals, return empty list
    if not validated:
        return []

    # Sort by start time
    validated.sort()

    # Merge overlapping/adjacent intervals
    merged = [validated[0]]

    for current_start, current_end in validated[1:]:
        last_start, last_end = merged[-1]

        # If current interval overlaps or is adjacent to the last one
        if current_start <= last_end:
            # Merge them by extending the end of the last interval
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # No overlap, add as new interval
            merged.append((current_start, current_end))

    return merged
