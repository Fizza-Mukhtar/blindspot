from decimal import Decimal, ROUND_HALF_UP

def format_bytes(n: int, binary: bool = False) -> str:
    """Format a byte count with SI or IEC prefix."""
    
    # Type checking: must be int, not bool
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(f"expected int, got {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Handle negative: extract sign and format magnitude
    if n < 0:
        return "-" + format_bytes(-n, binary)
    
    # Select ladder based on binary flag
    if binary:
        units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
        divisor = 1024
    else:
        units = ['B', 'kB', 'MB', 'GB', 'TB', 'PB']
        divisor = 1000
    
    # Find the largest unit whose next power is greater than n
    unit_index = 0
    while unit_index < len(units) - 1 and n >= divisor ** (unit_index + 1):
        unit_index += 1
    
    # Format the output
    if unit_index == 0:
        # For bytes, return as integer
        return f"{n} B"
    
    # For larger units, divide by the unit's divisor
    value = Decimal(n) / Decimal(divisor ** unit_index)
    
    # Round to 1 decimal place using half-up rounding
    rounded_value = value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    
    # If rounding caused overflow to next unit, promote and divide again
    if rounded_value >= divisor and unit_index < len(units) - 1:
        rounded_value = (rounded_value / divisor).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        unit_index += 1
    
    # Return formatted string
    return f"{rounded_value} {units[unit_index]}"
