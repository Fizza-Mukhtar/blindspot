import pytest
import impl


def test_basic_usd_formatting():
    """Test basic USD formatting with 2 decimal places."""
    exponents = {"USD": 2}
    result = impl.format_amount("1.5", "USD", exponents)
    assert result == "1.50"


def test_jpy_no_decimal_point():
    """Test JPY formatting with 0 decimal places (no decimal point)."""
    exponents = {"JPY": 0}
    result = impl.format_amount("1234.5", "JPY", exponents)
    assert result == "1234"


def test_kwd_three_decimal_places():
    """Test KWD formatting with 3 decimal places."""
    exponents = {"KWD": 3}
    result = impl.format_amount("1.2345", "KWD", exponents)
    assert result == "1.234"


def test_whole_number_padding_usd():
    """Test that whole numbers are padded with zeros."""
    exponents = {"USD": 2}
    result = impl.format_amount("5", "USD", exponents)
    assert result == "5.00"


def test_whole_number_jpy():
    """Test whole number in JPY has no decimal point."""
    exponents = {"JPY": 0}
    result = impl.format_amount("5", "JPY", exponents)
    assert result == "5"


def test_rounding_half_even_up():
    """Test half-even rounding when odd digit rounds up to even."""
    exponents = {"USD": 2}
    result = impl.format_amount("2.675", "USD", exponents)
    assert result == "2.68"


def test_rounding_half_even_down():
    """Test half-even rounding when even digit stays in place."""
    exponents = {"USD": 2}
    result = impl.format_amount("2.665", "USD", exponents)
    assert result == "2.66"


def test_negative_amount():
    """Test negative amount formatting."""
    exponents = {"USD": 2}
    result = impl.format_amount("-2.675", "USD", exponents)
    assert result == "-2.68"


def test_negative_zero_with_decimals():
    """Test that negative zero is normalized without sign."""
    exponents = {"USD": 2}
    result = impl.format_amount("-0.004", "USD", exponents)
    assert result == "0.00"


def test_negative_zero_without_decimals():
    """Test that negative zero in JPY has no decimal point."""
    exponents = {"JPY": 0}
    result = impl.format_amount("-0.4", "JPY", exponents)
    assert result == "0"


def test_explicit_plus_sign():
    """Test that explicit positive sign is removed."""
    exponents = {"USD": 2}
    result = impl.format_amount("+1.5", "USD", exponents)
    assert result == "1.50"


def test_scientific_notation():
    """Test scientific notation parsing."""
    exponents = {"USD": 2}
    result = impl.format_amount("1E+2", "USD", exponents)
    assert result == "100.00"


def test_extra_whitespace():
    """Test that surrounding whitespace is handled."""
    exponents = {"USD": 2}
    result = impl.format_amount("  1.5  ", "USD", exponents)
    assert result == "1.50"


def test_extra_decimal_places():
    """Test rounding of amounts with extra decimal places."""
    exponents = {"USD": 2}
    result = impl.format_amount("1.23456", "USD", exponents)
    assert result == "1.23"


def test_unknown_currency_raises_keyerror():
    """Test that unknown currency raises KeyError."""
    exponents = {"USD": 2}
    with pytest.raises(KeyError):
        impl.format_amount("1.5", "XYZ", exponents)


def test_invalid_amount_raises_valueerror():
    """Test that invalid amount string raises ValueError."""
    exponents = {"USD": 2}
    with pytest.raises(ValueError):
        impl.format_amount("abc", "USD", exponents)


def test_empty_string_raises_valueerror():
    """Test that empty string raises ValueError."""
    exponents = {"USD": 2}
    with pytest.raises(ValueError):
        impl.format_amount("", "USD", exponents)


def test_nan_raises_valueerror():
    """Test that NaN raises ValueError."""
    exponents = {"USD": 2}
    with pytest.raises(ValueError):
        impl.format_amount("NaN", "USD", exponents)


def test_infinity_raises_valueerror():
    """Test that Infinity raises ValueError."""
    exponents = {"USD": 2}
    with pytest.raises(ValueError):
        impl.format_amount("Infinity", "USD", exponents)


def test_currency_checked_before_amount():
    """Test that currency is checked before amount validation."""
    exponents = {"USD": 2}
    with pytest.raises(KeyError):
        impl.format_amount("abc", "XYZ", exponents)
