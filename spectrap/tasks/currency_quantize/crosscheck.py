"""Independent oracle for PAY-2291 (currency_quantize).

Deliberately does NOT use ``Decimal.quantize`` or any float/format path.  The
value is decomposed with ``Decimal.as_tuple()`` into exact integers and the
half-even rounding is then done with pure integer arithmetic (``divmod`` on a
power of ten, comparing ``2*remainder`` against the divisor).  Formatting is
done by string surgery on the rounded integer, so no formatting mini-language,
no ``str(Decimal)`` scientific-notation behaviour, and no context precision is
involved anywhere.
"""

from __future__ import annotations

import decimal
from decimal import Decimal

ORACLE_NOTES = """\
Basis
-----
* ISO 4217 "minor unit" / exponent column (via the maintenance-agency published
  table; iso.org itself serves 403 to non-browser clients).  Confirmed values:
  USD/EUR/GBP = 2, JPY/ISK/UGX = 0, KWD/BHD/OMR/TND = 3, CLF = 4.  The exponent
  is defined as "the number of digits after the decimal separator", which is
  exactly what the ticket asks the output to carry.
* Python decimal docs, rounding modes:  ROUND_HALF_EVEN -- "Round to nearest
  with ties going to nearest even integer."
* Python decimal docs, constructor grammar: the string is parsed "after leading
  and trailing whitespace characters, as well as underscores throughout, are
  removed", per the numeric-string EBNF.  Infinity/Inf/NaN/sNaN are inside that
  grammar but are not finite, so the ticket rejects them.

Algorithm (deliberately different from the obvious one)
-------------------------------------------------------
``Decimal(amount).as_tuple()`` -> (sign, digit tuple, exp10).  Let n be the
integer formed by the digits and k = exp10 + minor_units.  If k >= 0 the value
is already exact at the target scale (m = n * 10**k).  Otherwise divmod by
d = 10**-k and apply half-even by hand: 2*r > d -> up, 2*r < d -> down,
2*r == d -> up only if the quotient is odd.  Rounding is on the magnitude, so
the sign is reattached afterwards and dropped entirely when m == 0.  This is
exact for unbounded magnitude, which ``quantize`` is not: the decimal docs say
"if the length of the coefficient after the quantize operation would be greater
than precision, then an InvalidOperation is signaled", and the default context
precision is 28 digits.

Clauses checked
---------------
* half-even tie direction on both sides of the tie and on negatives;
* exponent 0 => no decimal point at all, and no "-0";
* zero padding when the input has fewer decimals than the exponent;
* KeyError raised before the amount is parsed;
* InvalidOperation translated to ValueError; non-finite rejected;
* positional output only, "however large the number".

Concerns with SPEC.md
---------------------
1. UNDER-DETERMINED (already listed in task.yaml open_questions, so noted not
   flagged): a negative or non-integer exponent in the caller's table.  This
   oracle treats a negative exponent as rounding to a power of ten and emits an
   integer with trailing zeros; nothing in the ticket decides this.
2. UNDER-DETERMINED and NOT in open_questions: what happens when ``amount`` is
   not a ``str`` at all (an ``int``, ``float`` or ``Decimal``).  The signature
   annotates ``str`` and the error clause says "If amount is not a string
   decimal.Decimal accepts ... raise ValueError", which reads as ValueError for
   a non-str, but ``Decimal`` itself accepts ints and floats happily, so an
   implementation that just calls ``Decimal(amount)`` will silently succeed.
   The generator never probes this, so it is untested either way.
3. POSSIBLE SPEC/IMPLEMENTATION TRAP: "There is no bound on magnitude" plus "no
   exponent notation however large the number" is incompatible with a bare
   ``Decimal.quantize`` under the default 28-digit context.  Any input whose
   quantised coefficient exceeds 28 digits (e.g. "1E+30" in USD) makes quantize
   signal InvalidOperation.  This oracle uses integer arithmetic and has no such
   bound.
"""

_EXP = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "JPY": 0,
    "ISK": 0,
    "UGX": 0,
    "KWD": 3,
    "BHD": 3,
    "OMR": 3,
    "TND": 3,
    "CLF": 4,
}


def _round_half_even(n: int, k: int) -> int:
    """Round the non-negative integer-scaled magnitude ``n * 10**k`` to an
    integer, ties to even.  ``n >= 0``."""
    if k >= 0:
        return n * (10 ** k)
    d = 10 ** (-k)
    q, r = divmod(n, d)
    twice = 2 * r
    if twice > d:
        return q + 1
    if twice < d:
        return q
    # Exact tie: keep the neighbour whose last kept digit is even.
    return q if q % 2 == 0 else q + 1


def oracle(amount, currency, exponents):
    # --- currency first, before the amount is even looked at -----------------
    minor_units = exponents[currency]  # KeyError by construction

    if not isinstance(minor_units, int) or isinstance(minor_units, bool):
        # Under-determined by the ticket; be strict rather than silently odd.
        raise TypeError("exponent must be an int")

    # --- amount --------------------------------------------------------------
    if not isinstance(amount, str):
        raise ValueError("amount must be a decimal string")
    try:
        value = Decimal(amount)
    except (decimal.InvalidOperation, ArithmeticError, ValueError, TypeError):
        raise ValueError(f"not a decimal amount: {amount!r}") from None
    if not value.is_finite():
        raise ValueError(f"not a finite amount: {amount!r}")

    sign, digits, exp10 = value.as_tuple()
    n = 0
    for d in digits:
        n = n * 10 + d

    m = _round_half_even(n, exp10 + minor_units)

    # --- positional formatting, no exponent notation, ever -------------------
    if minor_units > 0:
        body = str(m).rjust(minor_units + 1, "0")
        text = body[:-minor_units] + "." + body[-minor_units:]
    elif minor_units == 0:
        text = str(m)
    else:  # negative exponent: under-determined, emit a scaled integer
        text = str(m) + "0" * (-minor_units) if m else "0"

    if sign and m:
        text = "-" + text
    return text


_E = dict(_EXP)

KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # --- half-even ties, both directions (worked rows of the ticket, which
    #     match ROUND_HALF_EVEN "ties going to nearest even") -----------------
    (("2.675", "USD", dict(_E)), {}, "2.68"),
    (("2.665", "USD", dict(_E)), {}, "2.66"),
    (("8.835", "USD", dict(_E)), {}, "8.84"),
    (("-2.675", "USD", dict(_E)), {}, "-2.68"),
    (("-0.125", "USD", dict(_E)), {}, "-0.12"),
    # --- ISO 4217 exponent 0 (JPY): no decimal point at all ------------------
    (("1234.5", "JPY", dict(_E)), {}, "1234"),
    (("1235.5", "JPY", dict(_E)), {}, "1236"),
    (("-0.4", "JPY", dict(_E)), {}, "0"),
    (("1E-9", "ISK", dict(_E)), {}, "0"),
    # --- ISO 4217 exponent 3 and 4 -------------------------------------------
    (("1.2345", "KWD", dict(_E)), {}, "1.234"),
    (("1.2355", "BHD", dict(_E)), {}, "1.236"),
    (("0.12345", "CLF", dict(_E)), {}, "0.1234"),
    # --- padding, signs, whitespace, scientific input ------------------------
    (("5", "USD", dict(_E)), {}, "5.00"),
    (("+1.5", "USD", dict(_E)), {}, "1.50"),
    (("  1.5  ", "USD", dict(_E)), {}, "1.50"),
    (("1E+2", "USD", dict(_E)), {}, "100.00"),
    (("6.25e-2", "USD", dict(_E)), {}, "0.06"),
    (("-1.5e-3", "USD", dict(_E)), {}, "0.00"),
    (("-0.004", "USD", dict(_E)), {}, "0.00"),
    (("1234567.891", "USD", dict(_E)), {}, "1234567.89"),
    # --- unbounded magnitude, positional output only -------------------------
    (("1E+30", "USD", dict(_E)), {}, "1000000000000000000000000000000.00"),
    (("123456789012345678901234567.895", "USD", dict(_E)),
     {}, "123456789012345678901234567.90"),
    # --- errors ---------------------------------------------------------------
    (("abc", "USD", dict(_E)), {}, ("raises", "ValueError")),
    (("", "USD", dict(_E)), {}, ("raises", "ValueError")),
    (("1.2.3", "USD", dict(_E)), {}, ("raises", "ValueError")),
    (("Infinity", "USD", dict(_E)), {}, ("raises", "ValueError")),
    (("NaN", "USD", dict(_E)), {}, ("raises", "ValueError")),
    (("1.00", "XYZ", dict(_E)), {}, ("raises", "KeyError")),
    (("usd", "usd", dict(_E)), {}, ("raises", "KeyError")),
    # KeyError wins over ValueError: currency is checked first.
    (("abc", "XYZ", dict(_E)), {}, ("raises", "KeyError")),
]
