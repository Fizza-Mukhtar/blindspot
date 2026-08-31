class UnsatisfiableRange(Exception):
    """Raised when all range specifications are unsatisfiable."""
    pass


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """
    Resolve a Range: header into concrete byte offsets.
    
    Args:
        header: The Range header field value (e.g., "bytes=0-499")
        length: The total byte length of the representation
        
    Returns:
        A list of (first, last) tuples with inclusive offsets
        
    Raises:
        ValueError: If header is not a str or length is not a non-negative int
        UnsatisfiableRange: If length is 0, or all range specifications are unsatisfiable
    """
    # Validate arguments first
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if not isinstance(length, int):
        raise ValueError("length must be an int")
    if length < 0:
        raise ValueError("length must be non-negative")
    
    # Empty representation case
    if length == 0:
        raise UnsatisfiableRange("Cannot serve empty representation")
    
    # Try to parse the header
    result = _parse_and_resolve_ranges(header, length)
    if result is None:
        # Malformed header, serve whole representation
        return [(0, length - 1)]
    
    return result


def _parse_and_resolve_ranges(header: str, length: int) -> list[tuple[int, int]] | None:
    """
    Parse and resolve ranges. Returns None if header is malformed.
    Raises UnsatisfiableRange if all specs are unsatisfiable.
    """
    # Strip leading/trailing whitespace from the whole header
    header = header.strip(" \t")
    
    if not header:
        return None
    
    # Look for 'bytes='
    if '=' not in header:
        return None
    
    equals_idx = header.index('=')
    unit = header[:equals_idx]
    rest = header[equals_idx+1:]
    
    # Check unit: must be 'bytes' (case-insensitive)
    if unit.lower() != 'bytes':
        return None
    
    # Check that rest has no leading space (no space immediately after =)
    if rest and rest[0] in ' \t':
        return None
    
    # Parse the range specs
    spec_parts = rest.split(',')
    
    # Process each spec
    ranges = []
    has_any_spec = False
    
    for spec_part in spec_parts:
        # Strip whitespace around element
        spec = spec_part.strip(" \t")
        
        # Empty elements are skipped
        if not spec:
            continue
        
        has_any_spec = True
        
        # Parse the spec
        parsed = _parse_spec(spec, length)
        if parsed is None:
            # Malformed spec poisons the whole header
            return None
        
        if parsed is not False:  # False means unsatisfiable but well-formed
            ranges.append(parsed)
    
    if not has_any_spec:
        # Empty range set (no non-empty elements)
        return None
    
    if not ranges:
        # All specs were unsatisfiable
        raise UnsatisfiableRange("All range specifications are unsatisfiable")
    
    return ranges


def _parse_spec(spec: str, length: int) -> tuple[int, int] | bool | None:
    """
    Parse a single range spec.
    Returns: (first, last) tuple if satisfiable
             False if unsatisfiable but well-formed
             None if malformed
    """
    # Specs should not contain spaces (already stripped, but ensure no internal spaces)
    if ' ' in spec or '\t' in spec:
        return None
    
    # Check for bare '-'
    if spec == '-':
        return None
    
    # Check for '-suffix' format
    if spec.startswith('-'):
        suffix_str = spec[1:]
        if not suffix_str or not suffix_str.isdigit():
            return None
        suffix = int(suffix_str)
        
        # -0 is unsatisfiable
        if suffix == 0:
            return False
        
        # If suffix >= length, return whole representation
        if suffix >= length:
            return (0, length - 1)
        
        return (length - suffix, length - 1)
    
    # Check for 'first-last' or 'first-' format
    if '-' not in spec:
        return None
    
    # Split by '-' but only the first one
    dash_idx = spec.index('-')
    first_str = spec[:dash_idx]
    last_str = spec[dash_idx+1:]
    
    # first must be present and all digits
    if not first_str or not first_str.isdigit():
        return None
    
    first = int(first_str)
    
    # Check if it's 'first-' format (last is empty)
    if last_str == '':
        # first- format: from first to end
        if first >= length:
            return False
        return (first, length - 1)
    
    # 'first-last' format
    if not last_str.isdigit():
        return None
    
    last = int(last_str)
    
    # Check for invalid: last < first
    if last < first:
        return None
    
    # Check if first is unsatisfiable
    if first >= length:
        return False
    
    # Clamp last to length - 1
    last = min(last, length - 1)
    
    return (first, last)
