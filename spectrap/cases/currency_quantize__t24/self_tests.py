import impl
import pytest


def test_normal_amounts_different_currencies():
    """Test normal formatting with different currency exponents"""
    exponents = {'USD': 2, 'JPY': 0, 'KWD': 3, 'CLF': 4}
    
    # USD: 2 decimal places
    assert impl.format_amount("100.50", "USD", exponents) == "100.50"
    assert impl.format_amount("1.5", "USD", exponents) == "1.50"
    
    # JPY: 0 decimal places, no decimal point
    assert impl.format_amount("1234.5", "JPY", exponents) == "1234"
    assert impl.format_amount("1234", "JPY", exponents) == "1234"
    
    # KWD: 3 decimal places
    assert impl.format_amount("1.235", "KWD", exponents) == "1.235"
    
    # CLF: 4 decimal places
    assert impl.format_amount("1.2345", "CLF", exponents) == "1.2345"


def test_rounding_half_even():
    """Test ROUND_HALF_EVEN behavior"""
    exponents = {'USD': 2}
    
    # Exactly halfway: 2.675 rounds to 2.68 (round to even)
    assert impl.format_amount("2.675", "USD", exponents) == "2.68"
    
    # Exactly halfway: 2.665 rounds to 2.66 (round to even)
    assert impl.format_amount("2.665", "USD", exponents) == "2.66"
    
    # Negative rounds symmetrically
    assert impl.format_amount("-2.675", "USD", exponents) == "-2.68"
    assert impl.format_amount("-2.665", "USD", exponents) == "-2.66"


def test_input_format_variations():
    """Test different valid input formats"""
    exponents = {'USD': 2}
    
    # Scientific notation
    assert impl.format_amount("1E+2", "USD", exponents) == "100.00"
    assert impl.format_amount("1.5e-2", "USD", exponents) == "0.02"
    
    # Whitespace
    assert impl.format_amount("  2.50  ", "USD", exponents) == "2.50"
    
    # Explicit sign
    assert impl.format_amount("+2.50", "USD", exponents) == "2.50"
    
    # More or fewer decimals than target
    assert impl.format_amount("2.5", "USD", exponents) == "2.50"
    assert impl.format_amount("2.567", "USD", exponents) == "2.57"


def test_zero_handling():
    """Test zero and near-zero values"""
    exponents_usd = {'USD': 2}
    exponents_jpy = {'JPY': 0}
    
    # Positive zero
    assert impl.format_amount("0", "USD", exponents_usd) == "0.00"
    assert impl.format_amount("0", "JPY", exponents_jpy) == "0"
    
    # Negative zero becomes unsigned
    assert impl.format_amount("-0", "USD", exponents_usd) == "0.00"
    assert impl.format_amount("-0", "JPY", exponents_jpy) == "0"
    
    # Values that round to zero
    assert impl.format_amount("-0.004", "USD", exponents_usd) == "0.00"
    assert impl.format_amount("-0.4", "JPY", exponents_jpy) == "0"
    assert impl.format_amount("0.002", "USD", exponents_usd) == "0.00"


def test_negative_amounts():
    """Test negative number handling"""
    exponents = {'USD': 2}
    
    assert impl.format_amount("-1.00", "USD", exponents) == "-1.00"
    assert impl.format_amount("-0.50", "USD", exponents) == "-0.50"
    assert impl.format_amount("-100.567", "USD", exponents) == "-100.57"


def test_large_numbers_and_scientific_notation():
    """Test handling of large numbers and scientific notation"""
    exponents = {'USD': 2}
    
    # Large numbers with no exponent notation in output
    assert impl.format_amount("999999999.99", "USD", exponents) == "999999999.99"
    
    # Scientific notation with large exponents
    assert impl.format_amount("1E+10", "USD", exponents) == "10000000000.00"
    assert impl.format_amount("1.23E-2", "USD", exponents) == "0.01"


def test_invalid_amount_formats():
    """Test that invalid amount strings raise ValueError"""
    exponents = {'USD': 2}
    
    with pytest.raises(ValueError):
        impl.format_amount("", "USD", exponents)
    
    with pytest.raises(ValueError):
        impl.format_amount("abc", "USD", exponents)
    
    with pytest.raises(ValueError):
        impl.format_amount("1.2.3", "USD", exponents)
    
    with pytest.raises(ValueError):
        impl.format_amount("12,34", "USD", exponents)
    
    with pytest.raises(ValueError):
        impl.format_amount("$1.00", "USD", exponents)
    
    with pytest.raises(ValueError):
        impl.format_amount("1 000.00", "USD", exponents)


def test_non_finite_values():
    """Test that non-finite values raise ValueError"""
    exponents = {'USD': 2}
    
    with pytest.raises(ValueError):
        impl.format_amount("NaN", "USD", exponents)
    
    with pytest.raises(ValueError):
        impl.format_amount("sNaN", "USD", exponents)
    
    with pytest.raises(ValueError):
        impl.format_amount("Infinity", "USD", exponents)
    
    with pytest.raises(ValueError):
        impl.format_amount("-Infinity", "USD", exponents)


def test_unknown_currency():
    """Test that unknown currency raises KeyError"""
    exponents = {'USD': 2}
    
    with pytest.raises(KeyError):
        impl.format_amount("1.00", "XYZ", exponents)
    
    with pytest.raises(KeyError):
        impl.format_amount("1.00", "UNKNOWN", exponents)


def test_currency_lookup_precedence():
    """Test that currency lookup happens before amount validation"""
    exponents = {'USD': 2}
    
    # Unknown currency with invalid amount should raise KeyError, not ValueError
    with pytest.raises(KeyError):
        impl.format_amount("not_a_number", "XYZ", exponents)
