def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Merge overlapping or adjacent booking intervals into contiguous busy blocks.
    
    Converts raw reservation rows into merged intervals, dropping cancelled
    (zero-width) bookings. Intervals are half-open [start, end) in minutes.
    """
    validated = _validate_and_filter(intervals)
    
    if not validated:
        return []
    
    return _merge_intervals(validated)


def _validate_and_filter(intervals: list) -> list[tuple[int, int]]:
    """Validate input entries and filter out zero-width (cancelled) intervals."""
    validated: list[tuple[int, int]] = []
    
    for entry in intervals:
        # Check if entry is a tuple or list with exactly 2 elements
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise ValueError(f"Entry must be a two-element tuple or list, got {entry!r}")
        
        start, end = entry
        
        # Check if both elements are integers
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError(f"Entry must contain two integers, got {entry!r}")
        
        # Reject start > end
        if start > end:
            raise ValueError(f"({start}, {end})")
        
        # Skip zero-width intervals (cancelled bookings)
        if start < end:
            validated.append((start, end))
    
    return validated


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or adjacent intervals into contiguous blocks."""
    # Sort by start time
    intervals.sort()
    
    merged: list[tuple[int, int]] = []
    current_start, current_end = intervals[0]
    
    for start, end in intervals[1:]:
        if start <= current_end:
            # Overlapping or adjacent: merge by extending the end
            current_end = max(current_end, end)
        else:
            # Gap found: save current block and start a new one
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    
    # Append the final block
    merged.append((current_start, current_end))
    
    return merged
