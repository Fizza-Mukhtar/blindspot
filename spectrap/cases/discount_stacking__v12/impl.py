from decimal import Decimal, ROUND_HALF_EVEN


def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    """
    Apply a stack of promotions to a cart line total.
    
    Discounts are applied in order, with each discount applied to the 
    result of the previous discount (compounding effect).
    """
    
    # Validate and parse subtotal
    if not isinstance(subtotal, str):
        raise ValueError(f"subtotal must be a string, got {type(subtotal).__name__}")
    
    if not _is_valid_decimal_string(subtotal):
        raise ValueError(f"Invalid subtotal format: {subtotal}")
    
    running_total = Decimal(subtotal)
    
    # Check for negative subtotal
    if running_total < 0:
        raise ValueError(f"Subtotal cannot be negative: {subtotal}")
    
    # Round subtotal to 2 decimal places
    running_total = running_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    
    # If no discounts, return normalized subtotal
    if not discounts:
        return _format_decimal(running_total)
    
    # Apply each discount
    for discount in discounts:
        # Validate discount structure
        if not isinstance(discount, dict):
            raise ValueError(f"Discount must be a mapping, got {type(discount).__name__}")
        
        if "kind" not in discount:
            raise ValueError("Discount missing 'kind' field")
        
        if "value" not in discount:
            raise ValueError("Discount missing 'value' field")
        
        kind = discount["kind"]
        value = discount["value"]
        
        # Validate kind
        if kind not in ("percent", "amount"):
            raise ValueError(f"Invalid discount kind: {kind}")
        
        # Validate value
        if not isinstance(value, str):
            raise ValueError(f"Discount value must be a string, got {type(value).__name__}")
        
        if not _is_valid_decimal_string(value):
            raise ValueError(f"Invalid discount value format: {value}")
        
        decimal_value = Decimal(value)
        
        # Check for negative value
        if decimal_value < 0:
            raise ValueError(f"Discount value cannot be negative: {value}")
        
        # Apply discount based on kind
        if kind == "percent":
            # Check upper bound for percent
            if decimal_value > 100:
                raise ValueError(f"Percent discount cannot exceed 100: {value}")
            
            # Calculate: running_total × (100 - p) / 100
            running_total = running_total * (Decimal(100) - decimal_value) / Decimal(100)
        else:  # amount
            # Calculate: running_total - a
            running_total = running_total - decimal_value
        
        # Clamp at zero
        if running_total < 0:
            running_total = Decimal(0)
        
        # Round to 2 decimal places
        running_total = running_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    
    return _format_decimal(running_total)


def _is_valid_decimal_string(s: str) -> bool:
    """
    Check if a string matches the decimal grammar:
    optional `-`, one or more digits, optional `.` followed by one or more digits.
    """
    if not s:
        return False
    
    i = 0
    
    # Optional minus sign
    if s[i] == '-':
        i += 1
    
    # At least one digit required before optional decimal point
    if i >= len(s) or not s[i].isdigit():
        return False
    
    # Consume digits
    while i < len(s) and s[i].isdigit():
        i += 1
    
    # Optional decimal point followed by one or more digits
    if i < len(s):
        if s[i] != '.':
            return False
        i += 1
        
        # Must have at least one digit after decimal point
        if i >= len(s) or not s[i].isdigit():
            return False
        
        # Consume digits
        while i < len(s) and s[i].isdigit():
            i += 1
    
    # Should have consumed the entire string
    return i == len(s)


def _format_decimal(d: Decimal) -> str:
    """
    Format a Decimal as a string with exactly 2 decimal places.
    """
    # Quantize to 2 decimal places
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    
    # Convert to string
    return str(d)
