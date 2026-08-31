class UnsatisfiableRange(Exception):
    """Raised when all range specs are unsatisfiable."""
    pass


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """
    Resolve an HTTP Range header into concrete byte offsets.
    
    Args:
        header: The Range header field value (e.g., "bytes=0-499")
        length: The total length of the representation in bytes
    
    Returns:
        A list of (first, last) tuples, both inclusive
    
    Raises:
        ValueError: If header is not a str or length is not a non-negative int
        UnsatisfiableRange: If all specs are unsatisfiable or length is 0
    """
    # Validate arguments
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if not isinstance(length, int) or length < 0:
        raise ValueError("length must be a non-negative int")
    
    # Empty representation
    if length == 0:
        raise UnsatisfiableRange()
    
    # Try to parse the header
    ranges = _parse_header(header, length)
    
    if ranges is None:
        # All specs unsatisfiable
        raise UnsatisfiableRange()
    
    if not ranges:
        # Malformed header or no non-empty specs - serve whole representation
        return [(0, length - 1)]
    
    return ranges


def _parse_header(header: str, length: int) -> list[tuple[int, int]] | None:
    """
    Parse the Range header.
    
    Returns:
        - list of (first, last) tuples if at least one spec is satisfiable
        - empty list if header is malformed
        - None if all specs are unsatisfiable
    """
    header = header.strip()
    
    if not header:
        return []
    
    if '=' not in header:
        return []
    
    unit, ranges_str = header.split('=', 1)
    
    # Check no spaces around '='
    if unit != unit.rstrip() or ranges_str != ranges_str.lstrip():
        return []
    
    # Check unit (case-insensitive)
    if unit.lower() != 'bytes':
        return []
    
    # Parse range specifications
    specs = ranges_str.split(',')
    
    # Check for at least one non-empty spec
    non_empty_specs = [s.strip() for s in specs if s.strip()]
    if not non_empty_specs:
        return []
    
    # Parse each spec
    ranges = []
    has_satisfiable = False
    
    for spec in specs:
        spec = spec.strip()
        if not spec:
            continue  # Skip empty elements
        
        result = _parse_spec(spec, length)
        if result is None:
            # Malformed spec - poison the whole header
            return []
        
        if result is False:
            # Unsatisfiable spec
            continue
        
        ranges.append(result)
        has_satisfiable = True
    
    if not has_satisfiable:
        # All non-empty specs were unsatisfiable
        return None
    
    return ranges


def _parse_spec(spec: str, length: int) -> tuple[int, int] | bool | None:
    """
    Parse a single range spec.
    
    Returns:
        - (first, last) tuple if satisfiable
        - False if unsatisfiable
        - None if malformed
    """
    if '-' not in spec or spec.count('-') != 1:
        return None
    
    first_part, last_part = spec.split('-', 1)
    
    if not first_part and not last_part:
        return None  # Bare '-'
    
    # Check no spaces in parts
    if ' ' in first_part or '\t' in first_part or ' ' in last_part or '\t' in last_part:
        return None
    
    if not first_part:
        # Suffix range: -suffix
        if not last_part.isdigit():
            return None
        suffix = int(last_part)
        if suffix == 0:
            return False  # -0 is unsatisfiable
        first = max(0, length - suffix)
        return (first, length - 1)
    
    if not last_part:
        # Open range: first-
        if not first_part.isdigit():
            return None
        first = int(first_part)
        if first >= length:
            return False  # Unsatisfiable
        return (first, length - 1)
    
    # Closed range: first-last
    if not first_part.isdigit() or not last_part.isdigit():
        return None
    
    first = int(first_part)
    last = int(last_part)
    
    if last < first:
        return None  # Invalid range
    
    if first >= length:
        return False  # Unsatisfiable
    
    # Clamp last to length - 1
    return (first, min(last, length - 1))
