from decimal import Decimal, ROUND_HALF_EVEN
import re

def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """Apply a stack of promotions to a cart line total.
    
    Discounts are applied in order, with each discount applied to the running
    total from the previous step. Percentages compound rather than add.
    The running total is rounded to two decimal places after each step.
    """
    
    # Validate subtotal is a string
    if not isinstance(subtotal, str):
        raise ValueError(f"subtotal is not a str: {subtotal!r}")
    
    # Validate subtotal matches grammar: optional -, digits, optional . and digits
    if not re.match(r'^-?[0-9]+(\.[0-9]+)?$', subtotal):
        raise ValueError(f"subtotal is malformed: {subtotal}")
    
    # Convert and check for negative
    running_total = Decimal(subtotal)
    if running_total < 0:
        raise ValueError(f"subtotal is negative: {subtotal}")
    
    # Round to 2 decimal places
    running_total = running_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    
    # Apply each discount
    for discount in discounts:
        # Validate discount is a mapping
        if not isinstance(discount, dict):
            raise ValueError(f"discount is not a mapping: {discount!r}")
        
        # Validate discount has kind and value
        if "kind" not in discount:
            raise ValueError(f"discount is missing 'kind': {discount!r}")
        
        if "value" not in discount:
            raise ValueError(f"discount is missing 'value': {discount!r}")
        
        kind = discount["kind"]
        value_str = discount["value"]
        
        # Validate kind
        if kind not in ("percent", "amount"):
            raise ValueError(f"kind is invalid: {kind!r}")
        
        # Validate value is a string
        if not isinstance(value_str, str):
            raise ValueError(f"value is not a str: {value_str!r}")
        
        # Validate value matches grammar
        if not re.match(r'^-?[0-9]+(\.[0-9]+)?$', value_str):
            raise ValueError(f"value is malformed: {value_str}")
        
        value = Decimal(value_str)
        
        # Validate value is non-negative
        if value < 0:
            raise ValueError(f"value is negative: {value_str}")
        
        # Validate percent <= 100
        if kind == "percent" and value > 100:
            raise ValueError(f"percent value is greater than 100: {value_str}")
        
        # Apply the discount
        if kind == "percent":
            # running_total × (100 - p) / 100
            running_total = running_total * (100 - value) / 100
        else:  # kind == "amount"
            # running_total - a
            running_total = running_total - value
        
        # Clamp at zero
        if running_total < 0:
            running_total = Decimal('0.00')
        
        # Round to 2 decimal places
        running_total = running_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    
    # Return with exactly 2 decimal places
    return str(running_total)
