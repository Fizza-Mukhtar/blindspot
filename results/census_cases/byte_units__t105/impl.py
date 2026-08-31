from decimal import Decimal, ROUND_HALF_UP

def format_bytes(n: int, binary: bool = False) -> str:
    """Format a byte count with SI or IEC prefix."""
    
    # Validate input - must be an int, not a bool
    if type(n) is bool or not isinstance(n, int):
        raise TypeError(f"n must be an int, not {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Handle negative
    if n < 0:
        return "-" + format_bytes(-n, binary)
    
    # Define units
    if binary:
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
        divisor = 1024
    else:
        units = ["B", "kB", "MB", "GB", "TB", "PB"]
        divisor = 1000
    
    # Find the largest unit whose divisor is at most n
    unit_idx = 0
    for i in range(len(units) - 1, 0, -1):
        threshold = divisor ** i
        if n >= threshold:
            unit_idx = i
            break
    
    if unit_idx == 0:
        # Just bytes
        return f"{n} B"
    
    # Divide by the unit's divisor and round
    quotient = n / (divisor ** unit_idx)
    
    # Round half up to 1 decimal place
    rounded = Decimal(str(quotient)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    
    # Check if rounding carried to next unit
    if rounded >= divisor and unit_idx < len(units) - 1:
        # Promote to next unit
        unit_idx += 1
        rounded = (rounded / divisor).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    
    return f"{rounded} {units[unit_idx]}"
