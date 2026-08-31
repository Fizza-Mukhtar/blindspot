from decimal import Decimal, ROUND_HALF_EVEN
import re


def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """Apply a stack of promotions to a cart line total.
    
    Each discount is applied to the amount remaining after previous discounts.
    Percentages compound rather than add.
    """
    
    # Validate subtotal is a string
    if not isinstance(subtotal, str):
        raise ValueError(f"subtotal must be a string")
    
    # Validate subtotal format: optional -, one or more digits, optional . and one or more digits
    if not re.match(r'^-?\d+(\.\d+)?$', subtotal):
        raise ValueError(subtotal)
    
    # Parse as Decimal
    running = Decimal(subtotal)
    
    # Check for negative subtotal
    if running < 0:
        raise ValueError(subtotal)
    
    # Quantize subtotal to 2 decimal places
    running = running.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    
    # Apply each discount
    for discount in discounts:
        # Validate discount is a mapping
        if not isinstance(discount, dict):
            raise ValueError("discount is not a mapping")
        
        # Check for required keys
        if 'kind' not in discount:
            raise ValueError("discount missing 'kind'")
        if 'value' not in discount:
            raise ValueError("discount missing 'value'")
        
        kind = discount['kind']
        value = discount['value']
        
        # Validate kind is exactly "percent" or "amount"
        if kind not in ('percent', 'amount'):
            raise ValueError(kind)
        
        # Validate value is a string
        if not isinstance(value, str):
            raise ValueError(str(value))
        
        # Validate value format
        if not re.match(r'^-?\d+(\.\d+)?$', value):
            raise ValueError(value)
        
        # Parse value as Decimal
        decimal_value = Decimal(value)
        
        # Check for negative value
        if decimal_value < 0:
            raise ValueError(value)
        
        # Validate and apply based on kind
        if kind == 'percent':
            if decimal_value > 100:
                raise ValueError(value)
            # Apply percent discount: running × (100 - p) / 100
            running = running * (Decimal(100) - decimal_value) / Decimal(100)
        elif kind == 'amount':
            # Apply amount discount: running - a
            running = running - decimal_value
        
        # Clamp to zero
        if running < 0:
            running = Decimal(0)
        
        # Quantize to 2 decimal places
        running = running.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    
    # Ensure we return positive zero
    if running == 0:
        return "0.00"
    
    return str(running)
