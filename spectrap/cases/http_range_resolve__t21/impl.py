class UnsatisfiableRange(Exception):
    """Raised when a Range header cannot be satisfied."""
    pass


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """
    Resolve an HTTP Range header into concrete byte offset pairs.
    
    Args:
        header: The Range header value (e.g., "bytes=0-499")
        length: The total length of the representation in bytes
        
    Returns:
        A list of (first, last) tuples with inclusive offsets
        
    Raises:
        ValueError: If header or length arguments are invalid
        UnsatisfiableRange: If the representation is empty or all ranges are unsatisfiable
    """
    # Validate arguments
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if not isinstance(length, int):
        raise ValueError("length must be an int")
    if length < 0:
        raise ValueError("length must be >= 0")
    
    # Empty representation always raises
    if length == 0:
        raise UnsatisfiableRange()
    
    # Strip leading/trailing whitespace from entire header
    header = header.strip()
    
    # Check for empty header
    if not header:
        return [(0, length - 1)]
    
    # Split by '='
    if '=' not in header:
        return [(0, length - 1)]
    
    unit, range_spec = header.split('=', 1)
    
    # Check unit (case-insensitive)
    if unit.lower() != 'bytes':
        return [(0, length - 1)]
    
    # Parse range specs
    specs = range_spec.split(',')
    
    ranges = []
    any_spec = False
    
    for spec in specs:
        spec = spec.strip()
        
        # Skip empty specs
        if not spec:
            continue
        
        any_spec = True
        
        # Check for bare dash
        if spec == '-':
            return [(0, length - 1)]
        
        # Must contain a dash
        if '-' not in spec:
            return [(0, length - 1)]
        
        if spec.startswith('-'):
            # -suffix case
            suffix_str = spec[1:]
            
            if not suffix_str.isdigit():
                return [(0, length - 1)]
            
            suffix = int(suffix_str)
            
            # -0 is unsatisfiable
            if suffix == 0:
                continue
            
            # Take the last suffix bytes
            first = max(0, length - suffix)
            last = length - 1
            ranges.append((first, last))
        
        elif spec.endswith('-'):
            # first- case
            first_str = spec[:-1]
            
            if not first_str.isdigit():
                return [(0, length - 1)]
            
            first = int(first_str)
            
            # Unsatisfiable if first >= length
            if first >= length:
                continue
            
            ranges.append((first, length - 1))
        
        else:
            # first-last case
            first_str, last_str = spec.split('-', 1)
            
            if not first_str.isdigit() or not last_str.isdigit() or '-' in last_str:
                return [(0, length - 1)]
            
            first = int(first_str)
            last = int(last_str)
            
            # Invalid if last < first
            if last < first:
                return [(0, length - 1)]
            
            # Unsatisfiable if first >= length
            if first >= length:
                continue
            
            # Clamp last to length - 1
            last = min(last, length - 1)
            ranges.append((first, last))
    
    # If no specs were present, return whole object
    if not any_spec:
        return [(0, length - 1)]
    
    # If no satisfiable specs, raise
    if not ranges:
        raise UnsatisfiableRange()
    
    return ranges
