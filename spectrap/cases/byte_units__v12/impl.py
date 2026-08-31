def format_bytes(n: int, binary: bool = False) -> str:
    """Format a byte count using SI (powers of 1000) or IEC (powers of 1024) prefixes."""
    
    def round_half_up(value, decimals):
        """Round half up to the specified number of decimals."""
        multiplier = 10 ** decimals
        return int(value * multiplier + 0.5) / multiplier
    
    # Type check
    if type(n) is not int or isinstance(n, bool):
        raise TypeError(f"expected int, got {type(n).__name__}")
    
    # Handle zero
    if n == 0:
        return "0 B"
    
    # Handle sign
    if n < 0:
        return "-" + format_bytes(-n, binary)
    
    # Define units and divisor
    if binary:
        divisor = 1024
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    else:
        divisor = 1000
        units = ["B", "kB", "MB", "GB", "TB", "PB"]
    
    # Find the appropriate unit
    magnitude = float(n)
    unit_index = 0
    
    while magnitude >= divisor and unit_index < len(units) - 1:
        magnitude /= divisor
        unit_index += 1
    
    # Format output
    if unit_index == 0:  # bytes
        return f"{int(magnitude)} B"
    else:
        # Round to 1 decimal place (half up)
        rounded = round_half_up(magnitude, 1)
        
        # Check for promotion after rounding
        while rounded >= divisor and unit_index < len(units) - 1:
            unit_index += 1
            # Recalculate magnitude with the new unit
            magnitude = float(n) / (divisor ** unit_index)
            rounded = round_half_up(magnitude, 1)
        
        return f"{rounded:.1f} {units[unit_index]}"
