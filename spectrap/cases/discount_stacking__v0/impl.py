"""Apply a stack of promotions to a cart line total.

See PRICING-2317: discounts stack sequentially, each one applied to the
running total left by the previous one (matching Shopify's discount
combination behaviour), rather than being summed and applied once.
"""

import re
from collections.abc import Mapping
from decimal import Decimal, ROUND_HALF_EVEN

_MONEY_RE = re.compile(r"^-?\d+(\.\d+)?$")
_TWO_PLACES = Decimal("0.01")
_VALID_KINDS = ("percent", "amount")


def _round2(value: Decimal) -> Decimal:
    """Round to two decimal places, banker's rounding, normalising -0.00 to 0.00."""
    rounded = value.quantize(_TWO_PLACES, rounding=ROUND_HALF_EVEN)
    if rounded == 0:
        return Decimal("0.00")
    return rounded


def _parse_money_string(value: object, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{label} is not a str: {value!r}")
    if not _MONEY_RE.match(value):
        raise ValueError(f"{label} is malformed: {value!r}")
    return Decimal(value)


def _validate_discount(discount: object) -> tuple[str, Decimal]:
    if not isinstance(discount, Mapping):
        raise ValueError(f"discount is not a mapping: {discount!r}")
    if "kind" not in discount:
        raise ValueError(f"discount is missing 'kind': {discount!r}")
    if "value" not in discount:
        raise ValueError(f"discount is missing 'value': {discount!r}")

    kind = discount["kind"]
    if kind not in _VALID_KINDS:
        raise ValueError(f"kind is invalid: {kind!r}")

    value = discount["value"]
    value_dec = _parse_money_string(value, "value")
    if value_dec < 0:
        raise ValueError(f"value is negative: {value!r}")
    if kind == "percent" and value_dec > 100:
        raise ValueError(f"value exceeds 100 for a percent discount: {value!r}")

    return kind, value_dec


def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """Apply a stack of promotions to a cart line total.

    Discounts are applied in order, each one to the running total left by
    the previous one, rounding to two decimal places (banker's rounding)
    after every step. The running total is clamped at zero. Returns the
    final total as a decimal string with exactly two decimal places.

    Raises ValueError if the subtotal or any discount is malformed.
    """
    subtotal_dec = _parse_money_string(subtotal, "subtotal")
    if subtotal_dec < 0:
        raise ValueError(f"subtotal is negative: {subtotal!r}")

    running = _round2(subtotal_dec)

    for discount in discounts:
        kind, value_dec = _validate_discount(discount)

        if kind == "percent":
            raw = running * (Decimal(100) - value_dec) / Decimal(100)
        else:
            raw = running - value_dec
            if raw < 0:
                raw = Decimal(0)

        running = _round2(raw)

    return str(running)
