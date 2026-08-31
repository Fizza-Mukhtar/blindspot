from decimal import Decimal, ROUND_HALF_UP


def format_bytes(n: int, binary: bool = False) -> str:
    """Format a byte count with the appropriate SI or IEC prefix.
    
    Args:
        n: A byte count (int).
        binary: If True, use binary (IEC) prefixes (base 1024);
                otherwise use SI prefixes (base 1000).
    
    Returns:
        A formatted string like "1.5 kB" or "1.0 MiB".
    
    Raises:
        TypeError: If n is not an int, or if it's a bool.
    """
    # Type check: must be int, not bool
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(f"n must be an int, not {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Handle negative: format absolute value and prepend "-"
    if n < 0:
        return "-" + format_bytes(-n, binary)
    
    # Select prefix system
    if binary:
        divisor = 1024
        prefixes = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    else:
        divisor = 1000
        prefixes = ["B", "kB", "MB", "GB", "TB", "PB"]
    
    # Use Decimal for precise arithmetic and rounding
    magnitude = Decimal(n)
    divisor_dec = Decimal(divisor)
    
    # Find the largest unit whose divisor is at most the magnitude
    unit_index = 0
    while unit_index < len(prefixes) - 1 and magnitude >= divisor_dec:
        magnitude /= divisor_dec
        unit_index += 1
    
    # Format the value
    if unit_index == 0:
        # B unit: plain integer, no decimal point
        return f"{magnitude:.0f} B"
    else:
        # Other units: exactly one decimal place with half-up rounding
        rounded = magnitude.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        
        # Check if rounding carried to the next unit boundary
        if rounded >= divisor_dec and unit_index < len(prefixes) - 1:
            rounded = Decimal('1.0')
            unit_index += 1
        
        return f"{rounded} {prefixes[unit_index]}"
