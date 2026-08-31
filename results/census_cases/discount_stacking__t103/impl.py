from decimal import Decimal, ROUND_HALF_EVEN
import re

def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """Apply a stack of promotions to a cart line total.
    
    Each discount compounds on the running total from the previous discount.
    Discounts are applied in the order provided.
    """
    if not isinstance(subtotal, str):
        raise ValueError(str(subtotal))
    
    pattern = r'^-?\d+(\.\d+)?$'
    if not re.match(pattern, subtotal):
        raise ValueError(subtotal)
    
    value = Decimal(subtotal)
    if value < 0:
        raise ValueError(subtotal)
    
    running_total = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    
    for discount in discounts:
        running_total = _apply_discount(running_total, discount)
    
    if running_total == 0:
        return "0.00"
    return str(running_total)

def _apply_discount(total: Decimal, discount: dict) -> Decimal:
    """Apply a single discount to the running total."""
    if not isinstance(discount, dict):
        raise ValueError(str(discount))
    if "kind" not in discount:
        raise ValueError("discount missing 'kind'")
    if "value" not in discount:
        raise ValueError("discount missing 'value'")
    
    kind = discount["kind"]
    value_str = discount["value"]
    
    if kind not in ("percent", "amount"):
        raise ValueError(str(kind))
    
    if not isinstance(value_str, str):
        raise ValueError(str(value_str))
    
    pattern = r'^-?\d+(\.\d+)?$'
    if not re.match(pattern, value_str):
        raise ValueError(value_str)
    
    value = Decimal(value_str)
    if value < 0:
        raise ValueError(value_str)
    if kind == "percent" and value > 100:
        raise ValueError(value_str)
    
    if kind == "percent":
        result = total * (Decimal(100) - value) / Decimal(100)
    else:
        result = total - value
    
    if result < 0:
        result = Decimal(0)
    
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
