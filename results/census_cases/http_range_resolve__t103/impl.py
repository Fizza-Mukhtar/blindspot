class UnsatisfiableRange(Exception):
    """Raised when a Range header cannot be satisfied."""
    pass


def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    """
    Resolve a Range: header into concrete byte offsets.
    
    Args:
        header: The field value only (e.g., "bytes=0-499")
        length: The representation's exact current byte length
        
    Returns:
        A list of (first, last) tuples, both inclusive, in order
        
    Raises:
        ValueError: If header is not a str or length is not a non-negative int
        UnsatisfiableRange: If the representation is empty or all ranges are unsatisfiable
    """
    # Validate arguments
    if not isinstance(header, str):
        raise ValueError("header must be a string")
    if not isinstance(length, int) or length < 0:
        raise ValueError("length must be a non-negative integer")
    
    # Empty representation
    if length == 0:
        raise UnsatisfiableRange("Cannot satisfy any range for empty representation")
    
    # Parse the header
    ranges = _parse_range_header(header, length)
    if ranges is None:
        # Invalid header → serve whole object
        return [(0, length - 1)]
    
    # Filter unsatisfiable ranges
    satisfiable = [r for r in ranges if r is not None]
    if not satisfiable:
        raise UnsatisfiableRange("All ranges are unsatisfiable")
    
    return satisfiable


_INVALID = object()  # Sentinel for syntactically invalid specs


def _parse_range_header(header: str, length: int) -> list[tuple[int, int] | None] | None:
    """Parse a Range header into satisfiable and unsatisfiable ranges."""
    # Check for empty header
    if not header:
        return None
    
    # Strip and check for "bytes="
    stripped = header.strip()
    if not stripped.lower().startswith("bytes="):
        return None
    
    # Extract range_spec (everything after "bytes=")
    range_spec = stripped[6:]
    
    # Strip range_spec for leading/trailing spaces
    range_spec = range_spec.strip()
    if not range_spec:
        return None  # Empty range set
    
    # Split by comma and parse each element
    ranges = []
    elements = range_spec.split(',')
    has_nonempty = False
    
    for element in elements:
        element = element.strip()
        
        if not element:
            continue
        
        has_nonempty = True
        
        # Parse this element
        parsed = _parse_single_spec(element, length)
        if parsed is _INVALID:
            return None  # Invalid element poisons the whole header
        
        ranges.append(parsed)
    
    if not has_nonempty:
        return None  # No non-empty elements
    
    return ranges


def _parse_single_spec(spec: str, length: int):
    """Parse a single range spec and resolve to byte offsets."""
    # Check for spaces/tabs inside the spec
    if ' ' in spec or '\t' in spec:
        return _INVALID
    
    # Check for bare dash
    if spec == '-':
        return _INVALID
    
    # Count dashes (must be exactly one)
    dash_count = spec.count('-')
    if dash_count != 1:
        return _INVALID
    
    # Split by the dash
    idx = spec.index('-')
    first_part = spec[:idx]
    last_part = spec[idx + 1:]
    
    # Check that parts are all digits or empty
    if first_part and not first_part.isdigit():
        return _INVALID
    if last_part and not last_part.isdigit():
        return _INVALID
    
    # Parse based on format
    if first_part and last_part:
        # first-last format
        first = int(first_part)
        last = int(last_part)
        
        # Check for invalid spec (last < first)
        if last < first:
            return _INVALID
        
        # Check if satisfiable
        if first >= length:
            return None
        
        # Clamp last to length - 1
        last = min(last, length - 1)
        return (first, last)
    
    elif first_part:
        # first- format (open-ended)
        first = int(first_part)
        
        # Check if satisfiable
        if first >= length:
            return None
        
        return (first, length - 1)
    
    else:
        # -suffix format
        suffix = int(last_part)
        
        # -0 is unsatisfiable
        if suffix == 0:
            return None
        
        # suffix >= length means the whole object
        if suffix >= length:
            return (0, length - 1)
        
        # Return the last suffix bytes
        return (length - suffix, length - 1)
