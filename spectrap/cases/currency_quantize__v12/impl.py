from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation

def format_amount(amount: str, currency: str, exponents: dict[str, int]) -> str:
    """Format a monetary amount to its currency's minor units using exact decimal arithmetic."""
    
    # Check currency exists FIRST, before parsing amount
    if currency not in exponents:
        raise KeyError(currency)
    
    exponent = exponents[currency]
    
    # Parse amount as Decimal
    try:
        decimal_amount = Decimal(amount)
    except InvalidOperation:
        raise ValueError()
    
    # Check if the amount is finite
    if not decimal_amount.is_finite():
        raise ValueError()
    
    # Round to the currency's exponent using ROUND_HALF_EVEN
    quantize_decimal = Decimal(10) ** (-exponent)
    rounded = decimal_amount.quantize(quantize_decimal, rounding=ROUND_HALF_EVEN)
    
    # Normalize to remove leading sign from -0
    if rounded == 0:
        rounded = Decimal(0)
    
    # Format the output
    if exponent == 0:
        # No decimal point
        return str(int(rounded))
    else:
        # Format with exactly exponent decimal places
        return format(rounded, f'.{exponent}f')
