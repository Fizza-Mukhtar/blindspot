import pytest
import impl


def test_basic_usd():
    """Basic USD formatting with rounding to 2 decimals."""
    exponents = {"USD": 2}
    result = impl.format_amount("1.234", "USD", exponents)
    assert result == "1.23"


def test_basic_jpy():
    """JPY with 0 decimals, no decimal point in output."""
    exponents = {"JPY": 0}
    result = impl.format_amount("1234.5", "JPY", exponents)
    assert result == "1234"


def test_basic_kwd():
    """KWD with 3 decimals."""
    exponents = {"KWD": 3}
    result = impl.format_amount("1.2345", "KWD", exponents)
    assert result == "1.234"


def test_padding_zeros():
    """Amount with fewer decimals is padded with zeros."""
    exponents = {"USD": 2}
    result = impl.format_amount("5", "USD", exponents)
    assert result == "5.00"


def test_half_even_round_up():
    """Half-even rounding: 2.675 -> 2.68 (7 is odd, round up)."""
    exponents = {"USD": 2}
    result = impl.format_amount("2.675", "USD", exponents)
    assert result == "2.68"


def test_half_even_round_down():
    """Half-even rounding: 2.665 -> 2.66 (6 is even, stay)."""
    exponents = {"USD": 2}
    result = impl.format_amount("2.665", "USD", exponents)
    assert result == "2.66"


def test_half_even_jpy_up():
    """Half-even rounding: 1235.5 -> 1236 (5 is odd, round up)."""
    exponents = {"JPY": 0}
    result = impl.format_amount("1235.5", "JPY", exponents)
    assert result == "1236"


def test_half_even_jpy_down():
    """Half-even rounding: 1234.5 -> 1234 (4 is even, stay)."""
    exponents = {"JPY": 0}
    result = impl.format_amount("1234.5", "JPY", exponents)
    assert result == "1234"


def test_negative_amount():
    """Negative amount rounds correctly."""
    exponents = {"USD": 2}
    result = impl.format_amount("-2.675", "USD", exponents)
    assert result == "-2.68"


def test_negative_zero_usd():
    """Amount that rounds to zero loses its sign (USD)."""
    exponents = {"USD": 2}
    result = impl.format_amount("-0.004", "USD", exponents)
    assert result == "0.00"


def test_negative_zero_jpy():
    """Amount that rounds to zero loses its sign (JPY)."""
    exponents = {"JPY": 0}
    result = impl.format_amount("-0.4", "JPY", exponents)
    assert result == "0"


def test_positive_sign():
    """Amount with explicit positive sign."""
    exponents = {"USD": 2}
    result = impl.format_amount("+1.5", "USD", exponents)
    assert result == "1.50"


def test_scientific_notation():
    """Scientific notation: 1E+2 = 100."""
    exponents = {"USD": 2}
    result = impl.format_amount("1E+2", "USD", exponents)
    assert result == "100.00"


def test_whitespace():
    """Whitespace is stripped by Decimal parser."""
    exponents = {"USD": 2}
    result = impl.format_amount("  1.5  ", "USD", exponents)
    assert result == "1.50"


def test_large_number():
    """Large numbers work without issues."""
    exponents = {"USD": 2}
    result = impl.format_amount("123456789012345.67", "USD", exponents)
    assert result == "123456789012345.67"


def test_unknown_currency_keyerror():
    """Unknown currency raises KeyError."""
    exponents = {"USD": 2}
    with pytest.raises(KeyError):
        impl.format_amount("1.23", "GBP", exponents)


def test_unknown_currency_before_bad_amount():
    """Currency checked before amount parsing (KeyError before ValueError)."""
    exponents = {"USD": 2}
    with pytest.raises(KeyError):
        impl.format_amount("not a number", "XYZ", exponents)


def test_invalid_amount_empty_string():
    """Empty string is not a valid amount."""
    exponents = {"USD": 2}
    with pytest.raises(ValueError):
        impl.format_amount("", "USD", exponents)


def test_infinity_raises_valueerror():
    """Infinity is not a finite number."""
    exponents = {"USD": 2}
    with pytest.raises(ValueError):
        impl.format_amount("Infinity", "USD", exponents)


def test_nan_raises_valueerror():
    """NaN is not a finite number."""
    exponents = {"USD": 2}
    with pytest.raises(ValueError):
        impl.format_amount("NaN", "USD", exponents)
