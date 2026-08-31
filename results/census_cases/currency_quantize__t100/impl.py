from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation

def format_amount(amount: str, currency: str, exponents: dict[str, int]) -> str:
    """
    Format a monetary amount to its currency's minor units.
    
    Args:
        amount: The amount as a string (e.g., "1234.56")
        currency: ISO 4217 currency code (e.g., "USD", "JPY")
        exponents: Mapping of currency codes to number of decimal places
        
    Returns:
        Formatted amount string with exact decimal places for the currency
        
    Raises:
        KeyError: If currency is not in exponents
        ValueError: If amount is not a valid finite decimal number
    """
    # Look up currency first (KeyError before ValueError)
    exponent = exponents[currency]
    
    # Parse amount to Decimal
    try:
        decimal_amount = Decimal(amount)
    except InvalidOperation:
        raise ValueError("Invalid decimal amount")
    
    # Check if the value is finite
    if not decimal_amount.is_finite():
        raise ValueError("Non-finite amount")
    
    # Quantize to the correct number of decimal places
    if exponent == 0:
        quantize_exp = Decimal('1')
    else:
        quantize_exp = Decimal(10) ** -exponent
    
    quantized = decimal_amount.quantize(quantize_exp, rounding=ROUND_HALF_EVEN)
    
    # Handle negative zero
    if quantized == 0:
        quantized = abs(quantized)
    
    # Format without scientific notation using as_tuple
    sign, digits, exp = quantized.as_tuple()
    
    # Build the digit string
    digit_str = ''.join(str(d) for d in digits)
    
    # exp is the exponent - it tells us where the decimal point is
    if exp >= 0:
        # No fractional part, possibly with trailing zeros
        result = digit_str + '0' * exp
    else:
        # Fractional part exists
        # exp is negative, so -exp is how many digits are after the decimal
        num_frac_digits = -exp
        
        # Find where to split the digit_str
        int_digits = len(digit_str) - num_frac_digits
        
        if int_digits <= 0:
            # The whole number is fractional (e.g., 0.12)
            result = '0.' + '0' * (-int_digits) + digit_str
        else:
            # Split between integer and fractional parts
            result = digit_str[:int_digits] + '.' + digit_str[int_digits:]
    
    # Add sign if negative
    if sign:
        result = '-' + result
    
    return result
