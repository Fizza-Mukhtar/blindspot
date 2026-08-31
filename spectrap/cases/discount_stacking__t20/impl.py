from decimal import Decimal, ROUND_HALF_EVEN
import re

def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """Apply a stack of promotions to a cart line total using compound discounts."""
    
    # Validate and parse subtotal
    if not isinstance(subtotal, str):
        raise ValueError(f"{subtotal}")
    
    # Validate format: optional `-`, one or more digits, optionally `.` and one or more digits
    if not re.match(r'^-?[0-9]+(?:\.[0-9]+)?$', subtotal):
        raise ValueError(subtotal)
    
    # Parse as Decimal
    try:
        subtotal_decimal = Decimal(subtotal)
    except:
        raise ValueError(subtotal)
    
    # Check for negative (but "-0.00" should be okay as it equals 0)
    if subtotal_decimal < 0:
        raise ValueError(subtotal)
    
    # Quantize to two places
    running_total = subtotal_decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    
    # Apply each discount
    for discount in discounts:
        # Validate discount is a mapping
        if not isinstance(discount, dict):
            raise ValueError(str(discount))
        
        # Check for required keys
        if "kind" not in discount:
            raise ValueError(str(discount))
        if "value" not in discount:
            raise ValueError(str(discount))
        
        kind = discount["kind"]
        value_str = discount["value"]
        
        # Validate kind
        if kind not in ("percent", "amount"):
            raise ValueError(kind)
        
        # Validate value is a string
        if not isinstance(value_str, str):
            raise ValueError(str(value_str))
        
        # Validate value format
        if not re.match(r'^-?[0-9]+(?:\.[0-9]+)?$', value_str):
            raise ValueError(value_str)
        
        # Parse value
        try:
            value_decimal = Decimal(value_str)
        except:
            raise ValueError(value_str)
        
        # Check for negative value
        if value_decimal < 0:
            raise ValueError(value_str)
        
        # Check for percent > 100
        if kind == "percent" and value_decimal > 100:
            raise ValueError(value_str)
        
        # Apply discount
        if kind == "percent":
            # running × (100 − p) / 100
            running_total = running_total * (Decimal(100) - value_decimal) / Decimal(100)
        else:  # amount
            # running − a
            running_total = running_total - value_decimal
        
        # Quantize back to two places
        running_total = running_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
        
        # Clamp to 0
        if running_total < 0:
            running_total = Decimal('0.00')
    
    # Ensure result is never "-0.00"
    if running_total == 0:
        return "0.00"
    else:
        return str(running_total)
