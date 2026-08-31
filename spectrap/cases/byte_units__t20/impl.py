from decimal import Decimal, ROUND_HALF_UP


def format_bytes(n: int, binary: bool = False) -> str:
    """
    Format a byte count as a human-readable string with SI or IEC prefixes.
    
    Args:
        n: The byte count (must be an int, not bool)
        binary: If False (default), use SI prefixes (kB, MB, etc.).
                If True, use IEC prefixes (KiB, MiB, etc.).
    
    Returns:
        A formatted string like "1.0 kB" or "1.0 KiB"
    
    Raises:
        TypeError: If n is not an int or is a bool.
    """
    # Type check: n must be an int, but not bool
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(f"n must be an int, not {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Handle sign
    sign = "-" if n < 0 else ""
    n = abs(n)
    
    # Select divisor and units
    if binary:
        divisor = 1024
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    else:
        divisor = 1000
        units = ["B", "kB", "MB", "GB", "TB", "PB"]
    
    # Find the appropriate unit
    unit_index = 0
    magnitude = float(n)
    
    while unit_index < len(units) - 1 and magnitude >= divisor:
        magnitude /= divisor
        unit_index += 1
    
    # If we're at unit B, return as integer
    if unit_index == 0:
        return f"{sign}{int(magnitude)} B"
    
    # For other units, round to 1 decimal place using half-up
    d = Decimal(str(magnitude))
    rounded = float(d.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
    
    # Check for promotion to next unit
    if rounded >= divisor and unit_index < len(units) - 1:
        rounded /= divisor
        unit_index += 1
    
    return f"{sign}{rounded:.1f} {units[unit_index]}"
