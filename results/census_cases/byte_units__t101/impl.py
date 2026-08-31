from decimal import Decimal, ROUND_HALF_UP


def format_bytes(n: int, binary: bool = False) -> str:
    """Format a byte count with SI or IEC prefix.
    
    Args:
        n: A byte count (must be an int).
        binary: If True, use IEC binary prefixes (1024). If False (default), use SI decimal prefixes (1000).
    
    Returns:
        A formatted string with exactly one decimal place (except for bytes).
    
    Raises:
        TypeError: If n is not an int (including bool).
    """
    # Type check: must be int but not bool
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"n must be an int, not {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Handle sign
    if n < 0:
        return "-" + format_bytes(-n, binary=binary)
    
    # Define units
    if binary:
        divisor = 1024
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    else:
        divisor = 1000
        units = ["B", "kB", "MB", "GB", "TB", "PB"]
    
    # Find the appropriate unit index
    unit_index = 0
    magnitude = n
    
    while unit_index < len(units) - 1 and magnitude >= divisor:
        magnitude //= divisor
        unit_index += 1
    
    # Format based on unit index
    if unit_index == 0:
        # In bytes
        return f"{n} B"
    else:
        # Calculate the divisor for this unit
        divisor_power = divisor ** unit_index
        
        # Use Decimal for precise arithmetic
        d = Decimal(n) / Decimal(divisor_power)
        rounded = d.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        
        # Check if rounding caused promotion
        if rounded >= divisor and unit_index < len(units) - 1:
            # Promote to next unit
            divisor_power *= divisor
            d = Decimal(n) / Decimal(divisor_power)
            rounded = d.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            unit_index += 1
        
        unit = units[unit_index]
        return f"{rounded} {unit}"
