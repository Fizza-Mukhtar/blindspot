class UnsatisfiableRange(Exception):
    """Raised when a Range request cannot be satisfied."""
    pass


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """
    Resolve an RFC 7233 Range header into concrete byte offsets.
    
    Args:
        header: The Range header value (e.g., "bytes=0-499")
        length: The total length of the representation in bytes
        
    Returns:
        List of (first, last) inclusive byte offset pairs
        
    Raises:
        ValueError: If header is not a str or length is not a non-negative int
        UnsatisfiableRange: If all ranges are unsatisfiable or length is 0
    """
    # Validate arguments
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if not isinstance(length, int) or length < 0:
        raise ValueError("length must be a non-negative int")
    
    # Empty representation is always unsatisfiable
    if length == 0:
        raise UnsatisfiableRange()
    
    # Strip leading and trailing whitespace from header
    header = header.strip(' \t')
    
    # Empty header after stripping
    if not header:
        return [(0, length - 1)]
    
    # Find the '=' separator
    if '=' not in header:
        return [(0, length - 1)]
    
    eq_idx = header.index('=')
    unit = header[:eq_idx]
    range_set = header[eq_idx + 1:]
    
    # Verify unit is 'bytes' (case-insensitive)
    if unit.lower() != 'bytes':
        return [(0, length - 1)]
    
    # Check for spaces around the '=' (not allowed)
    if unit != unit.rstrip(' \t') or range_set != range_set.lstrip(' \t'):
        return [(0, length - 1)]
    
    # Split the range set by commas and process each spec
    specs = range_set.split(',')
    ranges = []
    seen_non_empty_spec = False
    
    for spec_raw in specs:
        # Strip spaces around each spec
        spec = spec_raw.strip(' \t')
        
        # Skip empty specs
        if not spec:
            continue
        
        seen_non_empty_spec = True
        
        # Verify no spaces inside the spec
        if ' ' in spec or '\t' in spec:
            return [(0, length - 1)]
        
        # Check for bare dash
        if spec == '-':
            return [(0, length - 1)]
        
        # Must contain a dash
        if '-' not in spec:
            return [(0, length - 1)]
        
        # Split on the first dash
        dash_idx = spec.find('-')
        first_part = spec[:dash_idx]
        last_part = spec[dash_idx + 1:]
        
        # Validate that non-empty parts contain only digits
        if first_part and not first_part.isdigit():
            return [(0, length - 1)]
        if last_part and not last_part.isdigit():
            return [(0, length - 1)]
        
        # At least one part must be non-empty
        if not first_part and not last_part:
            return [(0, length - 1)]
        
        # Resolve the range based on which parts are present
        if first_part and last_part:
            # Range: first-last
            first = int(first_part)
            last = int(last_part)
            
            # Validate: last must be >= first
            if last < first:
                return [(0, length - 1)]
            
            # Check if satisfiable: first < length
            if first < length:
                # Clamp last to length - 1
                last = min(last, length - 1)
                ranges.append((first, last))
        
        elif first_part:
            # Range: first- (to end)
            first = int(first_part)
            
            # Check if satisfiable: first < length
            if first < length:
                ranges.append((first, length - 1))
        
        else:
            # Range: -suffix (last N bytes)
            suffix = int(last_part)
            
            # -0 is unsatisfiable
            if suffix == 0:
                continue
            
            # Clamp suffix to length
            if suffix >= length:
                ranges.append((0, length - 1))
            else:
                ranges.append((length - suffix, length - 1))
    
    # Determine final result
    if ranges:
        return ranges
    elif seen_non_empty_spec:
        # Had specs but all were unsatisfiable
        raise UnsatisfiableRange()
    else:
        # No specs
        return [(0, length - 1)]
