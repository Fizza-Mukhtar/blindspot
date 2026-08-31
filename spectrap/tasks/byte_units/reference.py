"""Reference implementation for PLAT-2291 (SI / IEC byte-size rendering).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authorities:
  * SI decimal prefixes (BIPM) -- k = 10^3, and its symbol is a lowercase "k":
    https://www.bipm.org/en/measurement-units/si-prefixes
  * IEC 80000-13 binary prefixes -- Ki = 2^10, symbol "Ki" with an uppercase K:
    https://www.iec.ch/prefixes-binary-multiples
"""

from __future__ import annotations

# BIPM symbols.  Only "k" is lowercase; that asymmetry is the whole point.
_SI_UNITS: tuple[str, ...] = ("B", "kB", "MB", "GB", "TB", "PB")
# IEC 80000-13 symbols.  "Ki" is capitalised, unlike SI's "k".
_IEC_UNITS: tuple[str, ...] = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")


def _tenths_half_up(magnitude: int, divisor: int) -> int:
    """``magnitude / divisor`` rounded half up to one decimal, as tenths.

    Done in exact integer arithmetic: floor(x + 1/2) with x = 10*m/d is
    (20*m + d) // (2*d).  Binary floating point would resolve the exact .x5
    ties the wrong way (1150/1000 is not representable, and ``round`` is
    half-to-even in any case), and would lose precision entirely for the
    petabyte-scale magnitudes the spec allows.
    """
    return (20 * magnitude + divisor) // (2 * divisor)


def format_bytes(n: int, binary: bool = False) -> str:
    """Render ``n`` bytes using SI (default) or IEC 80000-13 prefixes."""
    # bool is a subclass of int, so it has to be rejected before the int check.
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"n must be an int number of bytes, got {type(n).__name__}")

    units = _IEC_UNITS if binary else _SI_UNITS
    base = 1024 if binary else 1000
    top = len(units) - 1

    # Sign is split off and re-attached; the magnitude alone drives the units.
    sign = "-" if n < 0 else ""
    magnitude = -n if n < 0 else n

    # Below one prefix step the value stays in bytes and is printed exactly:
    # no decimal point, no rounding, so 999 B and (in IEC mode) 1000 B.
    if magnitude < base:
        return f"{sign}{magnitude} {units[0]}"

    # Largest unit whose divisor still fits into the magnitude, capped at P/Pi.
    exponent = 1
    while exponent < top and magnitude >= base ** (exponent + 1):
        exponent += 1

    tenths = _tenths_half_up(magnitude, base**exponent)

    # Promotion: rounding to one decimal can reach the next unit boundary
    # (999_950 B -> 999.95 kB -> 1000.0 kB), and 1000.0 kB is spelled 1.0 MB.
    # Re-divide in the larger unit.  At the top of the ladder there is nowhere
    # to promote to, so the integer part simply keeps growing (1500.0 PB).
    while tenths >= base * 10 and exponent < top:
        exponent += 1
        tenths = _tenths_half_up(magnitude, base**exponent)

    # Exactly one fractional digit, one space, then the symbol.
    return f"{sign}{tenths // 10}.{tenths % 10} {units[exponent]}"
