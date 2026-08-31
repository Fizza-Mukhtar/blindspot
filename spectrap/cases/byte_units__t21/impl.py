def format_bytes(n: int, binary: bool = False) -> str:
    """
    Format a byte count with the correct SI or IEC prefix.
    
    Args:
        n: Number of bytes (must be an int, not bool or float)
        binary: If False (default), use SI prefixes (1000-based).
                If True, use IEC prefixes (1024-based).
    
    Returns:
        A formatted string like "1.2 MB" or "1.0 MiB"
    
    Raises:
        TypeError: If n is not an int, or if n is a bool
    """
    # Type check: must be int but not bool
    if type(n) is bool or not isinstance(n, int):
        raise TypeError(f"format_bytes() argument must be an int, not {type(n).__name__}")
    
    # Special case: zero
    if n == 0:
        return "0 B"
    
    # Handle negative numbers
    if n < 0:
        return "-" + format_bytes(-n, binary)
    
    # Define units and divisor based on binary flag
    if binary:
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
        divisor = 1024
    else:
        units = ["B", "kB", "MB", "GB", "TB", "PB"]
        divisor = 1000
    
    # Find the appropriate unit by dividing down
    magnitude = float(n)
    unit_index = 0
    
    while unit_index < len(units) - 1 and magnitude >= divisor:
        magnitude /= divisor
        unit_index += 1
    
    # Format the output
    if unit_index == 0:
        # For bytes, return as plain integer
        return f"{n} B"
    else:
        # For other units, round to 1 decimal place using half-up rounding
        # Multiply by 10, add 0.5, truncate to int to get half-up behavior
        scaled = magnitude * 10
        rounded_int = int(scaled + 0.5)
        
        # Handle overflow: if rounding caused us to reach the next unit boundary
        if rounded_int >= divisor * 10 and unit_index < len(units) - 1:
            unit_index += 1
            magnitude = rounded_int / 10 / divisor
            scaled = magnitude * 10
            rounded_int = int(scaled + 0.5)
        
        # Format with one decimal place, avoiding .1f for very large numbers
        integer_part = rounded_int // 10
        decimal_part = rounded_int % 10
        return f"{integer_part}.{decimal_part} {units[unit_index]}"
