"""Reference implementation for PRICING-2317 (stacked cart discounts).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: Shopify's discount-combination documentation,
https://help.shopify.com/en/manual/discounts/discount-combinations — combined
discounts are taken successively off the amount remaining after the previous
one, so percentages compound rather than add.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any

# SPEC "Money representation": optional '-', digits, optional '.' + digits.
# Deliberately stricter than Decimal(): no '+', no exponent, no whitespace,
# no 'NaN'/'Infinity', no empty string.
#
# `[0-9]` rather than `\d`, and `\Z` rather than `$`.  Python's `\d` matches any
# Unicode decimal digit and its `$` matches before a single trailing newline, so
# the shorter pattern silently accepted a money string ending in LF, and
# accepted non-ASCII numerals.  Both were found by the independent crosscheck
# oracle, not by inspection.
_NUMBER = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?\Z")

_CENT = Decimal("0.01")
_ZERO = Decimal("0.00")
_HUNDRED = Decimal("100")


def _parse_money(text: Any, label: str) -> Decimal:
    """Parse one decimal string, or raise naming it verbatim."""
    if not isinstance(text, str) or _NUMBER.match(text) is None:
        raise ValueError(f"malformed {label}: {text!r}")
    return Decimal(text)


def _round_cents(value: Decimal) -> Decimal:
    """Rule 3: two decimal places, ROUND_HALF_EVEN, applied at every step."""
    return value.quantize(_CENT, rounding=ROUND_HALF_EVEN)


def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """Apply a stack of promotions in list order and return the line total."""
    amount = _parse_money(subtotal, "subtotal")
    if amount < 0:
        raise ValueError(f"subtotal must not be negative: {subtotal}")

    # prec=60 keeps every intermediate product exact for any realistic cart;
    # all the rounding that matters is the explicit quantize in _round_cents.
    with localcontext() as ctx:
        ctx.prec = 60

        running = _round_cents(amount)  # rule 1

        for index, discount in enumerate(discounts):  # rule 2: list order
            if not isinstance(discount, dict):
                raise ValueError(f"discount {index} is not a mapping: {discount!r}")
            if "kind" not in discount or "value" not in discount:
                raise ValueError(f"discount {index} lacks kind/value: {discount!r}")

            kind = discount["kind"]
            raw = discount["value"]
            value = _parse_money(raw, f"discount {index} value")
            if value < 0:
                raise ValueError(f"discount value must not be negative: {raw}")

            if kind == "percent":
                if value > _HUNDRED:
                    raise ValueError(f"percent discount exceeds 100: {raw}")
                # running * (100 - p) / 100.  Multiplying by 0.01 instead of
                # dividing keeps the product exact before the single rounding.
                running = _round_cents(running * (_HUNDRED - value) * _CENT)
            elif kind == "amount":
                running = _round_cents(running - value)
            else:
                raise ValueError(f"unknown discount kind: {kind!r}")

            if running < _ZERO:  # rule 4: clamp, never go negative
                running = _ZERO

        if running == 0:  # "-0.00" is not an answer we ship
            running = _ZERO

    return str(running)
