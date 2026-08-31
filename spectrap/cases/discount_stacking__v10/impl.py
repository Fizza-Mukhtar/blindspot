import re
from decimal import Decimal, ROUND_HALF_EVEN


def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """
    Apply a stack of promotions to a cart line total.
    
    Discounts are applied sequentially, with each one applied to the result
    of the previous one. Each discount is rounded to 2 decimal places using
    banker's rounding.
    """
    
    # Validate and parse subtotal
    _validate_decimal_string(subtotal, "subtotal")
    running_total = Decimal(subtotal)
    
    # Check if subtotal is negative
    if running_total < 0:
        raise ValueError(f"subtotal is negative: {subtotal}")
    
    # Round subtotal to 2 decimal places
    running_total = running_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    
    # Apply each discount
    for discount in discounts:
        # Validate discount structure
        if not isinstance(discount, dict):
            raise ValueError(f"discount is not a mapping: {discount}")
        
        if "kind" not in discount:
            raise ValueError(f"discount is missing 'kind': {discount}")
        
        if "value" not in discount:
            raise ValueError(f"discount is missing 'value': {discount}")
        
        kind = discount["kind"]
        value_str = discount["value"]
        
        # Validate kind
        if kind not in ("percent", "amount"):
            raise ValueError(f"kind is not 'percent' or 'amount': {kind}")
        
        # Validate value format and content
        _validate_decimal_string(value_str, "discount value")
        decimal_value = Decimal(value_str)
        
        # Check if value is negative
        if decimal_value < 0:
            raise ValueError(f"discount value is negative: {value_str}")
        
        # Check if percent value is > 100
        if kind == "percent" and decimal_value > 100:
            raise ValueError(f"percent discount value is greater than 100: {value_str}")
        
        # Apply discount
        if kind == "percent":
            running_total = running_total * (Decimal(100) - decimal_value) / Decimal(100)
        else:  # kind == "amount"
            running_total = running_total - decimal_value
        
        # Round to 2 decimal places
        running_total = running_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        
        # Clamp at zero
        if running_total < 0:
            running_total = Decimal("0.00")
    
    # Normalize to positive zero and return as string with exactly 2 decimal places
    if running_total == 0:
        return "0.00"
    return str(running_total)


def _validate_decimal_string(value, field_name: str) -> None:
    """
    Validate that a value matches the decimal string grammar.
    
    Grammar: optional `-`, then one or more digits, then optionally 
    a `.` followed by one or more digits.
    
    Raises ValueError if the value is not a string or does not match the grammar.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} is not a string: {value}")
    
    pattern = r'^-?\d+(?:\.\d+)?$'
    if not re.match(pattern, value):
        raise ValueError(f"{field_name} does not match decimal grammar: {value}")
