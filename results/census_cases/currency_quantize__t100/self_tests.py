import pytest
import impl


def test_format_usd_basic():
    """Format basic USD amount with 2 decimal places."""
    result = impl.format_amount("1234.56", "USD", {"USD": 2})
    assert result == "1234.56"


def test_format_jpy_no_decimals():
    """JPY with 0 decimals should not have decimal point."""
    result = impl.format_amount("1234", "JPY", {"JPY": 0})
    assert result == "1234"


def test_format_three_decimals():
    """Currency with 3 decimal places (KWD)."""
    result = impl.format_amount("1.234", "KWD", {"KWD": 3})
    assert result == "1.234"


def test_format_four_decimals():
    """Currency with 4 decimal places (CLF)."""
    result = impl.format_amount("1.2345", "CLF", {"CLF": 4})
    assert result == "1.2345"


def test_zero_usd():
    """Zero is formatted as 0.00 for USD."""
    result = impl.format_amount("0", "USD", {"USD": 2})
    assert result == "0.00"


def test_zero_jpy():
    """Zero is formatted as 0 for JPY (no decimals)."""
    result = impl.format_amount("0", "JPY", {"JPY": 0})
    assert result == "0"


def test_round_half_even_up():
    """2.675 USD rounds to 2.68 (banker's rounding up)."""
    result = impl.format_amount("2.675", "USD", {"USD": 2})
    assert result == "2.68"


def test_round_half_even_down():
    """2.665 USD rounds to 2.66 (banker's rounding down)."""
    result = impl.format_amount("2.665", "USD", {"USD": 2})
    assert result == "2.66"


def test_round_negative():
    """Negative amounts round symmetrically: -2.675 → -2.68."""
    result = impl.format_amount("-2.675", "USD", {"USD": 2})
    assert result == "-2.68"


def test_negative_zero():
    """Negative zero becomes unsigned: -0.004 USD → 0.00."""
    result = impl.format_amount("-0.004", "USD", {"USD": 2})
    assert result == "0.00"


def test_padding_decimals():
    """Amounts with fewer decimals are zero-padded."""
    assert impl.format_amount("1.2", "USD", {"USD": 2}) == "1.20"
    assert impl.format_amount("1.2", "KWD", {"KWD": 3}) == "1.200"


def test_scientific_notation():
    """Scientific notation is handled: 1E+2 → 100.00, 1.5e-3 → 0.00."""
    assert impl.format_amount("1E+2", "USD", {"USD": 2}) == "100.00"
    assert impl.format_amount("1.5e-3", "USD", {"USD": 2}) == "0.00"


def test_whitespace_and_signs():
    """Whitespace is trimmed; plus sign removed; minus sign kept."""
    assert impl.format_amount(" 1.23 ", "USD", {"USD": 2}) == "1.23"
    assert impl.format_amount("+1.23", "USD", {"USD": 2}) == "1.23"
    assert impl.format_amount("-1.50", "USD", {"USD": 2}) == "-1.50"


def test_large_number_no_exponential():
    """Large numbers never use exponential notation."""
    result = impl.format_amount("123456789012345.67", "USD", {"USD": 2})
    assert result == "123456789012345.67"


def test_currency_not_found():
    """Currency not in exponents dict raises KeyError."""
    with pytest.raises(KeyError):
        impl.format_amount("1.23", "UNKNOWN", {"USD": 2})


def test_invalid_amount_empty_or_malformed():
    """Various malformed amounts raise ValueError."""
    invalid = ["", "abc", "1.2.3", "12,34", "$1.00", "1 000.00"]
    for amount in invalid:
        with pytest.raises(ValueError):
            impl.format_amount(amount, "USD", {"USD": 2})


def test_non_finite_numbers():
    """NaN and Infinity raise ValueError."""
    non_finite = ["NaN", "sNaN", "Infinity", "-Infinity"]
    for amount in non_finite:
        with pytest.raises(ValueError):
            impl.format_amount(amount, "USD", {"USD": 2})


def test_currency_checked_before_amount():
    """Currency is validated before amount to raise KeyError first."""
    with pytest.raises(KeyError):
        impl.format_amount("invalid_amount", "UNKNOWN", {"USD": 2})
