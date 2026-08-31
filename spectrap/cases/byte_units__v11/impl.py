def format_bytes(n: int, binary: bool = False) -> str:
    """Format a byte count with SI or IEC prefix.
    
    Args:
        n: Number of bytes (must be an int, not bool).
        binary: If False (default), use SI prefixes (B, kB, MB, GB, TB, PB).
                If True, use IEC prefixes (B, KiB, MiB, GiB, TiB, PiB).
    
    Returns:
        Formatted string with value and unit.
    
    Raises:
        TypeError: If n is not an int, or if n is a bool.
    """
    # Validate input: must be int, but not bool
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"n must be int, not {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Extract sign
    is_negative = n < 0
    n = abs(n)
    
    # Set up units and divisor
    if binary:
        divisor = 1024
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    else:
        divisor = 1000
        units = ["B", "kB", "MB", "GB", "TB", "PB"]
    
    # Find the initial unit: largest unit whose divisor is <= n
    unit_index = 0
    while unit_index < len(units) - 1 and n >= divisor ** (unit_index + 1):
        unit_index += 1
    
    # Format the output
    if unit_index == 0:
        # B unit: plain integer with no decimal point
        result = f"{n} B"
    else:
        # Other units: one decimal place with round half up and promotion
        while True:
            divisor_for_unit = divisor ** unit_index
            
            # Calculate value with one decimal place using round half up
            n_times_10 = n * 10
            quotient = n_times_10 // divisor_for_unit
            remainder = n_times_10 % divisor_for_unit
            
            # Round half up: if remainder >= divisor_for_unit / 2, round up
            if remainder * 2 >= divisor_for_unit:
                value_times_10 = quotient + 1
            else:
                value_times_10 = quotient
            
            # Check if we need to promote to the next unit
            if value_times_10 >= divisor * 10 and unit_index < len(units) - 1:
                unit_index += 1
                continue  # Recalculate with the new unit
            else:
                # No promotion needed
                value = value_times_10 / 10
                result = f"{value:.1f} {units[unit_index]}"
                break
    
    # Add sign if negative
    if is_negative:
        result = "-" + result
    
    return result
