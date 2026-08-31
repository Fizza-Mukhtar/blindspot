def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Merge overlapping booking intervals into non-overlapping busy blocks.
    
    Intervals are half-open: [start, end) where start is included, end is not.
    Zero-width intervals (start == end) are silently dropped.
    """
    cleaned = []
    
    for entry in intervals:
        # Validate it's a tuple or list
        if not isinstance(entry, (tuple, list)):
            raise ValueError("Entry must be tuple or list")
        
        # Validate it has exactly 2 elements
        if len(entry) != 2:
            raise ValueError("Entry must have exactly 2 elements")
        
        # Extract values
        start, end = entry[0], entry[1]
        
        # Validate both are integers
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Entry elements must be integers")
        
        # Validate start <= end
        if start > end:
            raise ValueError(f"({start}, {end})")
        
        # Skip zero-width intervals (cancellations)
        if start < end:
            cleaned.append((start, end))
    
    # Handle empty case
    if not cleaned:
        return []
    
    # Sort by start time
    cleaned.sort()
    
    # Merge adjacent/overlapping intervals
    merged = []
    current_start, current_end = cleaned[0]
    
    for start, end in cleaned[1:]:
        if start <= current_end:
            # Overlapping or adjacent - extend current interval
            current_end = max(current_end, end)
        else:
            # Gap exists - save current interval and start new one
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    
    # Don't forget the last interval
    merged.append((current_start, current_end))
    
    return merged
