from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation

def format_amount(amount: str, currency: str, exponents: dict[str, int]) -> str:
    """Format a monetary amount to its currency's minor units.
    
    Args:
        amount: A decimal string representation of the amount.
        currency: ISO 4217 alphabetic currency code.
        exponents: Mapping of currency codes to their number of minor units.
    
    Returns:
        A string with exactly the appropriate number of decimal places.
    
    Raises:
        KeyError: If currency is not in the exponents dictionary.
        ValueError: If amount is not a valid decimal or is non-finite.
    """
    # Check currency first (required: before validating amount)
    if currency not in exponents:
        raise KeyError(currency)
    
    exponent = exponents[currency]
    
    # Parse and validate the amount
    try:
        decimal_amount = Decimal(amount)
    except InvalidOperation:
        raise ValueError(f"Invalid amount: {amount}")
    
    # Check if the value is finite
    if not decimal_amount.is_finite():
        raise ValueError(f"Amount must be finite: {amount}")
    
    # Create the quantize exponent: 10^(-exponent)
    if exponent == 0:
        quantize_exp = Decimal('1')
    else:
        quantize_exp = Decimal(10) ** -exponent
    
    # Round to the appropriate number of decimal places using half-even rounding
    rounded = decimal_amount.quantize(quantize_exp, rounding=ROUND_HALF_EVEN)
    
    # Normalize negative zero
    if rounded.is_zero():
        if exponent == 0:
            return '0'
        else:
            return '0.' + '0' * exponent
    
    # Format as a fixed-point decimal string with the exact number of decimal places
    return format(rounded, f'.{exponent}f')
