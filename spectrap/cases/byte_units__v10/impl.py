from decimal import Decimal, ROUND_HALF_UP


def format_bytes(n: int, binary: bool = False) -> str:
    """Format a byte count with SI or IEC prefix.
    
    Args:
        n: Number of bytes (must be an int, not bool, float, or other type)
        binary: If False (default), use SI prefixes (base 1000).
                If True, use IEC prefixes (base 1024).
    
    Returns:
        Formatted string with appropriate unit symbol.
    
    Raises:
        TypeError: If n is not an int (including if n is a bool).
    """
    # Type check - must be int but not bool
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(f"expected int, got {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Handle sign
    negative = n < 0
    magnitude = abs(n)
    
    # Define the units and divisor
    if binary:
        divisor = 1024
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    else:
        divisor = 1000
        units = ["B", "kB", "MB", "GB", "TB", "PB"]
    
    # Find the appropriate unit: largest unit whose divisor <= magnitude
    unit_index = 0
    for i in range(len(units) - 1, 0, -1):
        if magnitude >= divisor ** i:
            unit_index = i
            break
    
    # Format the number
    if unit_index == 0:
        # B unit: plain integer with no decimal point
        result = str(magnitude)
    else:
        # Divide by the appropriate power of the divisor
        divisor_power = divisor ** unit_index
        value = magnitude / divisor_power
        
        # Round half up to 1 decimal place
        rounded = _round_half_up(value, 1)
        
        # Check for promotion: if rounded value >= divisor and not at top unit,
        # promote to next unit and re-round
        if rounded >= divisor and unit_index < len(units) - 1:
            unit_index += 1
            divisor_power = divisor ** unit_index
            value = magnitude / divisor_power
            rounded = _round_half_up(value, 1)
        
        # Format with exactly 1 decimal place
        result = f"{rounded:.1f}"
    
    # Construct final result with sign and unit
    sign = "-" if negative else ""
    return f"{sign}{result} {units[unit_index]}"


def _round_half_up(value: float, decimals: int) -> float:
    """Round a value half-up to the specified number of decimal places.
    
    This uses Decimal for exact rounding, avoiding floating-point quirks.
    """
    d = Decimal(str(value))
    rounded = d.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
    return float(rounded)
