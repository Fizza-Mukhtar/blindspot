"""Independent oracle for PLAT-2291 (format_bytes).

Written from SPEC.md plus the two cited standards (BIPM SI prefixes and the
IEC 80000-13 binary prefixes as tabulated by NIST).  Deliberately structured
differently from the obvious `while mag >= base: mag //= base` implementation.
"""

from __future__ import annotations

import decimal
from decimal import Decimal

ORACLE_NOTES = """\
Basis
-----
* Decimal ladder: BIPM SI prefixes (https://www.bipm.org/en/measurement-units/si-prefixes).
  The BIPM table gives kilo = k = 10^3 with a LOWERCASE k, and mega = M = 10^6,
  giga = G = 10^9, tera = T = 10^12, peta = P = 10^15, all uppercase.  So the
  decimal ladder symbols are B, kB, MB, GB, TB, PB.
* Binary ladder: IEC 80000-13 binary prefixes.  www.iec.ch/prefixes-binary-multiples
  returns HTTP 403 to automated fetches, so I used the NIST reproduction of the
  same IEC table (https://physics.nist.gov/cuu/Units/binary.html), which gives
  kibi = Ki = 2^10, mebi = Mi = 2^20, gibi = Gi = 2^30, tebi = Ti = 2^40,
  pebi = Pi = 2^50 (and exbi = Ei = 2^60, which this ticket does not use).  Note
  the UPPERCASE K in Ki.  NIST's own worked examples, copied into KNOWN_VALUES:
  "one mebibyte: 1 MiB = 2^20 B = 1 048 576 B" vs "one megabyte: 1 MB = 10^6 B
  = 1 000 000 B", and "one gibibyte: 1 GiB = 2^30 B = 1 073 741 824 B" vs
  "one gigabyte: 1 GB = 10^9 B = 1 000 000 000 B".

Algorithm (deliberately different from the reference's likely shape)
--------------------------------------------------------------------
No repeated-division loop and no float arithmetic anywhere.  Instead:

  1. The unit ladder is a static decision table of (divisor, symbol) pairs.
  2. The *smallest* index k whose rounded display value is strictly below the
     base is selected, scanning upward, with k = 5 as a forced fallback.  This
     is equivalent to "pick the largest unit with divisor <= magnitude, then
     promote while the rounded value reaches the base", but it derives the
     answer in one pass instead of picking-then-fixing, so a promotion bug in
     the reference cannot be mirrored by a promotion bug here.
  3. The one-decimal rounding is delegated to the standard library:
     `Decimal.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)`, evaluated in a
     `localcontext` whose precision is set large enough that the division
     magnitude/divisor is EXACT (both 1000**k and 1024**k have terminating
     decimal reciprocals, needing at most 10*k fractional digits).  So the
     half-up decision is made on the exact rational value, never on a float.

Clauses checked
---------------
* BIPM prefix table: symbol case for k / M / G / T / P.
* IEC 80000-13 (via NIST): Ki/Mi/Gi/Ti/Pi symbols and their 2^(10k) factors,
  and the explicit 1 MiB = 1 048 576 B vs 1 MB = 1 000 000 B contrast.
* SPEC.md "How the number is rendered", "Promotion after rounding",
  "Above the top of the ladder", "Errors".

Ambiguities / possible spec problems
------------------------------------
* NOT a defect, just noted: the standards define exbi/Ei and exa/E and beyond,
  but the ticket caps the ladder at PB/PiB and lets the integer part grow
  ("1024.0 PiB", "1500.0 PB").  That is a product decision that departs from
  the standards' own ladders; it is stated unambiguously in SPEC.md, so the
  oracle follows SPEC.md.  task.yaml already lists the >10^24 question as an
  intentional open question.
* SPEC.md's promotion rule says "if the rounded display value would be 1000.0
  or greater in SI (1024.0 or greater in IEC) and a larger unit is available,
  move up one unit and round again there".  Written as a single step it could
  in principle need to repeat; it cannot in practice (after promoting, the
  value is ~1.0), but the oracle applies it as a fixed point anyway.
* SPEC.md is silent on whether a non-bool int SUBCLASS is acceptable.  The
  generator never produces one; the oracle accepts it (isinstance-based),
  matching "n must be an int".
* `binary` type is deliberately under-determined per task.yaml; the oracle
  treats it as a plain truth value.
"""

# (divisor, SI symbol, IEC symbol) -- a static decision table, index == ladder rung.
_LADDER: tuple[tuple[int, str, str], ...] = (
    (1, "B", "B"),
    (1, "kB", "KiB"),  # divisors filled in below; symbols are the payload
    (1, "MB", "MiB"),
    (1, "GB", "GiB"),
    (1, "TB", "TiB"),
    (1, "PB", "PiB"),
)

_SI_SYMBOLS = [row[1] for row in _LADDER]
_IEC_SYMBOLS = [row[2] for row in _LADDER]

_TOP = len(_LADDER) - 1  # 5 -> PB / PiB

_ONE_TENTH = Decimal("0.1")


def _display(magnitude: int, divisor: int) -> Decimal:
    """magnitude/divisor rounded half up to one decimal, exactly (no floats)."""
    # Enough precision that the quotient is represented exactly: the integer
    # part has len(str(magnitude)) digits, and 1/1024**k terminates after at
    # most 10*k decimal digits (1/1000**k after 3*k).
    needed = len(str(magnitude)) + 10 * len(str(divisor)) + 20
    with decimal.localcontext() as ctx:
        ctx.prec = needed
        ctx.rounding = decimal.ROUND_HALF_UP
        quotient = Decimal(magnitude) / Decimal(divisor)
        return quotient.quantize(_ONE_TENTH, rounding=decimal.ROUND_HALF_UP)


def oracle(n, binary=False):
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(
            "n must be an int (bool is not a byte count), got "
            f"{type(n).__name__}"
        )

    base = 1024 if binary else 1000
    symbols = _IEC_SYMBOLS if binary else _SI_SYMBOLS

    sign = "-" if n < 0 else ""
    magnitude = -n if n < 0 else n

    # Rung 0 is special: printed as a bare integer, no decimal point.
    if magnitude < base:
        return f"{sign}{magnitude} {symbols[0]}"

    # Scan upward for the smallest rung whose half-up display value is below
    # the base; that single condition subsumes both "largest unit whose divisor
    # is <= the magnitude" and the post-rounding promotion rule.
    limit = Decimal(base)
    for k in range(1, _TOP + 1):
        value = _display(magnitude, base**k)
        if value < limit or k == _TOP:
            return f"{sign}{value} {symbols[k]}"

    raise AssertionError("unreachable")  # pragma: no cover


# Expected values taken from the standards' own worked examples where they
# exist, and from the arithmetic the standards define where they do not.
KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # --- NIST/IEC 80000-13 worked examples, verbatim byte counts ---
    ((1_048_576,), {"binary": True}, "1.0 MiB"),   # 1 MiB = 2^20 B = 1 048 576 B
    ((1_000_000,), {}, "1.0 MB"),                  # 1 MB  = 10^6 B = 1 000 000 B
    ((1_073_741_824,), {"binary": True}, "1.0 GiB"),  # 1 GiB = 2^30 B
    ((1_000_000_000,), {}, "1.0 GB"),              # 1 GB  = 10^9 B
    ((1024,), {"binary": True}, "1.0 KiB"),        # kibi = Ki = 2^10, uppercase K
    ((1000,), {}, "1.0 kB"),                       # BIPM kilo = k = 10^3, lowercase k
    ((2**40,), {"binary": True}, "1.0 TiB"),       # tebi = Ti = 2^40
    ((10**12,), {}, "1.0 TB"),                     # BIPM tera = T = 10^12
    ((2**50,), {"binary": True}, "1.0 PiB"),       # pebi = Pi = 2^50
    ((10**15,), {}, "1.0 PB"),                     # BIPM peta = P = 10^15
    # --- the ladders must not mix ---
    ((1024,), {}, "1.0 kB"),                       # 1024 B = 1.024 kB
    ((1000,), {"binary": True}, "1000 B"),         # 1000 B < 1 KiB
    ((1_000_000,), {"binary": True}, "976.6 KiB"),  # 10^6/1024 = 976.5625
    ((1_048_576,), {}, "1.0 MB"),                  # 2^20 B = 1.048576 MB
    # --- SPEC.md rendering rules ---
    ((0,), {}, "0 B"),
    ((999,), {}, "999 B"),
    ((1150,), {}, "1.2 kB"),                       # half-up on an exact .x5 tie
    ((999_949,), {}, "999.9 kB"),
    ((999_950,), {}, "1.0 MB"),                    # promotion after rounding
    ((1_048_575,), {"binary": True}, "1.0 MiB"),   # 1023.999... KiB -> promoted
    ((-1500,), {}, "-1.5 kB"),
    ((-1500,), {"binary": True}, "-1.5 KiB"),
    ((1_500_000_000_000_000_000,), {}, "1500.0 PB"),
    ((2**60,), {"binary": True}, "1024.0 PiB"),
    # --- errors ---
    ((1000.0,), {}, ("raises", "TypeError")),
    ((True,), {}, ("raises", "TypeError")),
    (("1000",), {}, ("raises", "TypeError")),
    ((None,), {}, ("raises", "TypeError")),
]
