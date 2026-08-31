from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation


def format_amount(amount: str, currency: str, exponents: dict[str, int]) -> str:
    """
    Format a monetary amount to its currency's minor units using exact decimal arithmetic.
    
    Args:
        amount: String representation of the monetary amount
        currency: ISO 4217 currency code
        exponents: Mapping of currency codes to their number of decimal places
    
    Returns:
        Formatted amount string with exact number of decimals for the currency
    
    Raises:
        KeyError: If currency is not in exponents
        ValueError: If amount is not a valid finite number
    """
    # Look up exponent first, before processing amount
    exponent = exponents[currency]  # Raises KeyError if not found
    
    # Parse the amount using Decimal
    try:
        value = Decimal(amount)
    except InvalidOperation:
        raise ValueError("Invalid amount")
    
    # Check for non-finite values
    if not value.is_finite():
        raise ValueError("Amount must be finite")
    
    # Create quantize exponent
    if exponent == 0:
        quantize_exp = Decimal('1')
    else:
        quantize_exp = Decimal(10) ** -exponent
    
    # Quantize to the correct number of decimal places
    quantized = value.quantize(quantize_exp, rounding=ROUND_HALF_EVEN)
    
    # Handle zero (both positive and negative zero)
    if quantized == 0:
        if exponent == 0:
            return '0'
        else:
            return '0.' + '0' * exponent
    
    # Format to string without exponent notation
    result = format(quantized, f'.{exponent}f')
    
    return result
