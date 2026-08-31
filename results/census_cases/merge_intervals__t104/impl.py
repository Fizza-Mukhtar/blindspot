def merge_bookings(intervals: list[tuple[int, int] | list[int]]) -> list[tuple[int, int]]:
    """
    Merge overlapping booking intervals into a single list of busy blocks.
    
    Takes a list of half-open intervals [start, end) and returns a sorted,
    non-overlapping list of merged intervals. Zero-width intervals are
    dropped silently. Raises ValueError for invalid intervals.
    """
    valid_intervals = []
    
    for entry in intervals:
        # Validate structure
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise ValueError("Entry must be a 2-element tuple or list")
        
        start, end = entry
        
        # Validate types
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Interval entries must be integers")
        
        # Validate order
        if start > end:
            raise ValueError(f"({start}, {end})")
        
        # Skip zero-width intervals (cancellations)
        if start != end:
            valid_intervals.append((start, end))
    
    # Empty input or all cancellations
    if not valid_intervals:
        return []
    
    # Sort by start time
    sorted_intervals = sorted(valid_intervals)
    
    # Merge overlapping/adjacent intervals
    merged = []
    current_start, current_end = sorted_intervals[0]
    
    for start, end in sorted_intervals[1:]:
        if start <= current_end:
            # Overlapping or adjacent (no gap), merge
            current_end = max(current_end, end)
        else:
            # Gap exists, finalize current and start new block
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    
    # Append final block
    merged.append((current_start, current_end))
    
    return merged
