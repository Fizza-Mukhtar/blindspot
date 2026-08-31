def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Merge overlapping booking intervals into non-overlapping blocks.
    
    Intervals are half-open [start, end) in minutes since midnight.
    Zero-width intervals are dropped. Adjacent and overlapping intervals are merged.
    """
    # Validate input and collect valid intervals in one pass
    processed = []
    for item in intervals:
        # Check if it's a tuple or list
        if not isinstance(item, (tuple, list)):
            raise ValueError("Entry must be a tuple or list")
        
        # Check if it has exactly 2 elements
        if len(item) != 2:
            raise ValueError("Entry must have exactly 2 elements")
        
        start, end = item
        
        # Check if both are integers
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Entry must contain integers")
        
        # Check if start <= end
        if start > end:
            raise ValueError(f"({start}, {end})")
        
        # Skip zero-width intervals (cancelled bookings)
        if start != end:
            processed.append((start, end))
    
    # If no valid intervals, return empty list
    if not processed:
        return []
    
    # Sort by start time
    processed.sort()
    
    # Merge overlapping/adjacent intervals
    merged = [processed[0]]
    for start, end in processed[1:]:
        last_start, last_end = merged[-1]
        
        # If this interval overlaps or is adjacent to the last one, merge
        if start <= last_end:
            # Merge: extend the end if necessary
            merged[-1] = (last_start, max(last_end, end))
        else:
            # No overlap, add as new interval
            merged.append((start, end))
    
    return merged
