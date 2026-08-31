from decimal import Decimal, ROUND_HALF_UP


def format_bytes(n: int, binary: bool = False) -> str:
    """Format a byte count with the correct SI or IEC prefix.
    
    Args:
        n: A count of bytes (must be an int, not bool).
        binary: If False (default), use SI prefixes (powers of 1000).
                If True, use IEC binary prefixes (powers of 1024).
    
    Returns:
        A formatted string like "1.5 GB" or "1.4 GiB".
    
    Raises:
        TypeError: If n is not an int, or if n is a bool.
    """
    # Type checking: reject non-int types and bool (even though bool subclasses int)
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(f"n must be an int, not {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Handle negative: format the absolute value and prepend the sign
    if n < 0:
        return "-" + format_bytes(-n, binary)
    
    # Define units and divisor based on prefix system
    if binary:
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
        divisor = 1024
    else:
        units = ["B", "kB", "MB", "GB", "TB", "PB"]
        divisor = 1000
    
    # Find the appropriate unit: the largest unit whose divisor is at most n
    unit_idx = 0
    while unit_idx < len(units) - 1 and n >= divisor ** (unit_idx + 1):
        unit_idx += 1
    
    # Format the value in the chosen unit
    if unit_idx == 0:
        # B unit: always show as plain integer with no decimal point
        value_str = str(n)
        symbol = units[0]
    else:
        # Other units: divide by the unit's divisor and format with exactly 1 decimal place
        divisor_power = divisor ** unit_idx
        value = Decimal(n) / Decimal(divisor_power)
        # Round to 1 decimal place using half-up rounding
        rounded = value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        
        # Check if rounding caused promotion to the next unit
        # This handles cases like 999.95 kB rounding to 1000.0 kB = 1.0 MB
        while rounded >= Decimal(divisor) and unit_idx < len(units) - 1:
            unit_idx += 1
            divisor_power = divisor ** unit_idx
            value = Decimal(n) / Decimal(divisor_power)
            rounded = value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        
        value_str = str(rounded)
        symbol = units[unit_idx]
    
    return f"{value_str} {symbol}"
