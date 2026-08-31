def format_bytes(n: int, binary: bool = False) -> str:
    """Render a byte count as a human-readable string with an SI or IEC prefix.

    ``binary=False`` (the default) uses SI decimal prefixes (divisor 1000,
    units B/kB/MB/GB/TB/PB). ``binary=True`` uses IEC binary prefixes
    (divisor 1024, units B/KiB/MiB/GiB/TiB/PiB). The chosen unit is the
    largest whose divisor does not exceed the magnitude, capped at the top
    of the ladder (PB/PiB). Values are rounded half up to one decimal place,
    and a rounded value that reaches the next unit's boundary is promoted
    and re-rounded there. ``n`` must be a plain ``int`` (``bool`` excluded).
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"n must be an int, not {type(n).__name__}")

    sign = "-" if n < 0 else ""
    magnitude = abs(n)

    if binary:
        base = 1024
        units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    else:
        base = 1000
        units = ("B", "kB", "MB", "GB", "TB", "PB")

    if magnitude == 0:
        return "0 B"

    unit_index = 0
    for i in range(len(units) - 1, 0, -1):
        if magnitude >= base ** i:
            unit_index = i
            break

    if unit_index == 0:
        return f"{sign}{magnitude} B"

    while True:
        divisor = base ** unit_index
        tenths, remainder = divmod(magnitude * 10, divisor)
        if remainder * 2 >= divisor:
            tenths += 1
        if tenths >= base * 10 and unit_index < len(units) - 1:
            unit_index += 1
            continue
        break

    whole, frac = divmod(tenths, 10)
    return f"{sign}{whole}.{frac} {units[unit_index]}"
