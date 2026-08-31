from decimal import Decimal, ROUND_HALF_EVEN
import re

def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """Apply a stack of promotions to a cart line total.
    
    Each discount compounds on the amount left after previous discounts.
    Uses decimal arithmetic for precision to the cent.
    """
    
    # Grammar for decimal strings: optional minus, one or more digits,
    # optional dot followed by one or more digits
    DECIMAL_PATTERN = r'^-?\d+(\.\d+)?$'
    
    # Validate and parse subtotal
    if not isinstance(subtotal, str):
        raise ValueError("subtotal must be a string")
    
    if not re.match(DECIMAL_PATTERN, subtotal):
        raise ValueError(f"subtotal malformed: {subtotal}")
    
    running_total = Decimal(subtotal)
    
    if running_total < 0:
        raise ValueError(f"subtotal is negative: {subtotal}")
    
    # Quantize subtotal to 2 decimal places
    running_total = running_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    
    # Apply each discount in order
    for discount in discounts:
        # Validate discount structure
        if not isinstance(discount, dict):
            raise ValueError("discount must be a mapping")
        
        if "kind" not in discount:
            raise ValueError("discount missing 'kind'")
        
        if "value" not in discount:
            raise ValueError("discount missing 'value'")
        
        kind = discount["kind"]
        value = discount["value"]
        
        # Validate kind
        if kind not in ("percent", "amount"):
            raise ValueError(f"kind is not 'percent' or 'amount': {kind}")
        
        # Validate value is a string
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        
        # Validate value format
        if not re.match(DECIMAL_PATTERN, value):
            raise ValueError(f"value malformed: {value}")
        
        value_decimal = Decimal(value)
        
        # Validate value is not negative
        if value_decimal < 0:
            raise ValueError(f"value is negative: {value}")
        
        # For percent, validate it doesn't exceed 100
        if kind == "percent" and value_decimal > 100:
            raise ValueError(f"value exceeds 100 for percent: {value}")
        
        # Apply the discount
        if kind == "percent":
            # Percentage discount: running × (100 − p) / 100
            running_total = running_total * (Decimal(100) - value_decimal) / Decimal(100)
        else:  # kind == "amount"
            # Fixed amount discount: running − a
            running_total = running_total - value_decimal
        
        # Quantize to 2 decimal places after each step
        running_total = running_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
        
        # Clamp to non-negative
        if running_total < 0:
            running_total = Decimal('0.00')
    
    # Convert to string with exactly 2 decimal places
    result_str = str(running_total)
    
    # Ensure we never return "-0.00"
    if result_str == "-0.00":
        result_str = "0.00"
    
    return result_str
