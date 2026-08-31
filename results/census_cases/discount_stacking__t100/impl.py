from decimal import Decimal, ROUND_HALF_EVEN
import re

def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """Apply a stack of promotions to a cart line total.
    
    Discounts are applied sequentially, each operating on the total left after
    the previous discount. Percentages compound rather than add.
    
    Args:
        subtotal: A decimal string in major units (e.g., "100.00")
        discounts: A list of discount dicts with 'kind' and 'value' keys
        
    Returns:
        The final total as a decimal string with exactly two decimal places
        
    Raises:
        ValueError: If inputs are malformed or invalid
    """
    
    # Validate and parse subtotal
    if not isinstance(subtotal, str):
        raise ValueError(f"subtotal is not a str: {subtotal!r}")
    
    # Grammar: optional `-`, one or more digits, optionally `.` and one or more digits
    if not re.match(r'^-?\d+(\.\d+)?$', subtotal):
        raise ValueError(f"subtotal is malformed: {subtotal!r}")
    
    # Parse
    running_total = Decimal(subtotal)
    
    # Check that subtotal is non-negative (compared numerically)
    if running_total < 0:
        raise ValueError(f"subtotal is negative: {subtotal!r}")
    
    # Quantize the starting total to 2 decimal places
    running_total = running_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    
    # Apply each discount
    for discount in discounts:
        # Validate discount structure
        if not isinstance(discount, dict):
            raise ValueError(f"discount is not a mapping: {discount!r}")
        
        if 'kind' not in discount:
            raise ValueError(f"discount is missing 'kind': {discount!r}")
        
        if 'value' not in discount:
            raise ValueError(f"discount is missing 'value': {discount!r}")
        
        kind = discount['kind']
        value_str = discount['value']
        
        # Validate kind
        if kind not in ('percent', 'amount'):
            raise ValueError(f"kind is not 'percent' or 'amount': {kind!r}")
        
        # Validate value
        if not isinstance(value_str, str):
            raise ValueError(f"value is not a str: {value_str!r}")
        
        # Grammar check
        if not re.match(r'^\d+(\.\d+)?$', value_str):
            raise ValueError(f"value is malformed: {value_str!r}")
        
        value = Decimal(value_str)
        
        # For percent, value cannot be greater than 100
        if kind == 'percent' and value > 100:
            raise ValueError(f"percent value is greater than 100: {value_str!r}")
        
        # Apply the discount
        if kind == 'percent':
            running_total = running_total * (100 - value) / 100
        else:  # amount
            running_total = running_total - value
        
        # Clamp to 0 if negative
        if running_total < 0:
            running_total = Decimal('0')
        
        # Quantize
        running_total = running_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    
    # Format with exactly two decimal places
    if running_total == 0:
        return "0.00"
    
    return str(running_total)
