class UnsatisfiableRange(Exception):
    """Raised when no satisfiable byte range can be resolved."""
    pass


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """
    Resolve an HTTP Range header to concrete byte offsets.
    
    Args:
        header: The field value of a Range header (e.g., "bytes=0-499")
        length: The exact current byte length of the representation
    
    Returns:
        A list of (first, last) tuples, both inclusive, in header order
    
    Raises:
        ValueError: If header is not a str or length is not a non-negative int
        UnsatisfiableRange: If the representation is empty or all ranges are unsatisfiable
    """
    # Validate arguments
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if not isinstance(length, int) or length < 0:
        raise ValueError("length must be a non-negative int")
    
    # Empty representation
    if length == 0:
        raise UnsatisfiableRange("Cannot resolve range on empty representation")
    
    # Try to parse the header
    try:
        ranges = _parse_range_header(header, length)
        return ranges
    except UnsatisfiableRange:
        # All specs unsatisfiable (but header was valid)
        raise
    except:
        # Any other error means malformed header
        return [(0, length - 1)]


def _parse_range_header(header: str, length: int) -> list[tuple[int, int]]:
    """Parse a Range header value and return list of (first, last) tuples."""
    
    # Strip leading/trailing whitespace from whole value
    header = header.strip()
    
    if not header:
        raise ValueError("Empty string")
    
    # Find '=' (must not have space before or after)
    eq_pos = header.find('=')
    if eq_pos == -1:
        raise ValueError("Missing '='")
    
    # No space around '='
    if eq_pos > 0 and header[eq_pos - 1] in (' ', '\t'):
        raise ValueError("Space before '='")
    if eq_pos < len(header) - 1 and header[eq_pos + 1] in (' ', '\t'):
        raise ValueError("Space after '='")
    
    unit = header[:eq_pos]
    range_set = header[eq_pos + 1:]
    
    # Check unit (case-insensitive)
    if unit.lower() != 'bytes':
        raise ValueError("Unsupported unit")
    
    # Parse range-set (comma-separated list)
    range_specs = range_set.split(',')
    
    ranges = []
    has_satisfiable = False
    has_nonempty = False
    
    for spec in range_specs:
        # Strip whitespace around spec
        spec = spec.strip()
        
        # Skip empty specs
        if not spec:
            continue
        
        has_nonempty = True
        
        # Check for spaces inside spec
        if ' ' in spec or '\t' in spec:
            raise ValueError("Space inside spec")
        
        result = _parse_range_spec(spec, length)
        if result is not None:
            ranges.append(result)
            has_satisfiable = True
    
    if not has_nonempty:
        raise ValueError("Empty range set")
    
    if not has_satisfiable:
        raise UnsatisfiableRange("No satisfiable ranges")
    
    return ranges


def _parse_range_spec(spec: str, length: int) -> tuple[int, int] | None:
    """Parse a single range spec and return (first, last) or None."""
    
    if not spec:
        raise ValueError("Empty spec")
    
    if spec == '-':
        raise ValueError("Bare '-'")
    
    hyphen_count = spec.count('-')
    if hyphen_count != 1:
        raise ValueError("Invalid hyphens")
    
    hyphen_pos = spec.find('-')
    
    if hyphen_pos == 0:
        # Suffix range: -suffix
        suffix_str = spec[1:]
        if not suffix_str.isdigit():
            raise ValueError("Invalid suffix")
        
        suffix = int(suffix_str)
        
        if suffix == 0:
            return None
        
        first = max(0, length - suffix)
        last = length - 1
        return (first, last)
    
    elif hyphen_pos == len(spec) - 1:
        # Range from first to end: first-
        first_str = spec[:-1]
        if not first_str.isdigit():
            raise ValueError("Invalid first")
        
        first = int(first_str)
        
        if first >= length:
            return None
        
        last = length - 1
        return (first, last)
    
    else:
        # Range first-last
        first_str = spec[:hyphen_pos]
        last_str = spec[hyphen_pos + 1:]
        
        if not first_str.isdigit():
            raise ValueError("Invalid first")
        if not last_str.isdigit():
            raise ValueError("Invalid last")
        
        first = int(first_str)
        last = int(last_str)
        
        if last < first:
            raise ValueError("last < first")
        
        if first >= length:
            return None
        
        if last >= length:
            last = length - 1
        
        return (first, last)
