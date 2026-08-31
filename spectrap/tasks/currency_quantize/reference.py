"""Reference implementation for PAY-2291 (ISO 4217 minor-unit quantisation).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authorities:
  - ISO 4217 minor units ("exponent" column):
    https://www.iso.org/iso-4217-currency-codes.html
  - decimal.ROUND_HALF_EVEN:
    https://docs.python.org/3/library/decimal.html#decimal.ROUND_HALF_EVEN
"""

from __future__ import annotations

import decimal
from decimal import Decimal


def format_amount(amount: str, currency: str, exponents: dict[str, int]) -> str:
    """Round ``amount`` to ``currency``'s minor units and render it plainly."""
    # The lookup happens first, so an unknown code is a KeyError even when the
    # amount is also malformed.  Exact match: ISO 4217 codes are upper-case
    # already and the caller's table is authoritative, so no normalisation.
    exponent = exponents[currency]

    # Exact decimal arithmetic, straight from the string.  Routing through
    # float would perturb every half-way value (float("2.675") < 2.675) and
    # silently flip the half-even decision.
    try:
        value = Decimal(amount)
    except (decimal.InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"not a valid decimal amount: {amount!r}") from exc
    if not value.is_finite():
        # "NaN"/"Infinity" parse fine but are not money.
        raise ValueError(f"not a valid decimal amount: {amount!r}")

    # 1e-exponent, built from the digit tuple so no arithmetic context is
    # involved: (sign=0, digits=(1,), exp=-exponent).
    unit = Decimal((0, (1,), -exponent))

    with decimal.localcontext() as ctx:
        # quantize() signals InvalidOperation if the result would need more
        # significant digits than the context allows; the default 28 is not
        # enough for large amounts, and the ticket puts no bound on magnitude.
        ctx.prec = max(28, max(value.adjusted(), 0) + exponent + 3)
        ctx.rounding = decimal.ROUND_HALF_EVEN
        quantized = value.quantize(unit)

    # Decimal keeps the sign of a negative value that rounded to zero
    # (Decimal("-0.004") -> Decimal("-0.00")); money does not.
    if quantized.is_zero() and quantized.is_signed():
        quantized = -quantized

    # After quantize() the coefficient exponent is -exponent <= 0, so str()
    # never falls back to scientific notation: it is already the plain
    # positional form, with exactly `exponent` decimals and no point at all
    # when the exponent is 0.
    return str(quantized)
