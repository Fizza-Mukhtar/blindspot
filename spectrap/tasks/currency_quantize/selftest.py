"""Authoritative examples for PAY-2291.

Every assertion here is traceable either to a cited standard or to an explicit
sentence of SPEC.md, not to the reference implementation's incidental
behaviour.  ``make verify-corpus`` runs this against ``reference.py`` in CI,
which is what lets the README claim that ground-truth labels are verified by
construction rather than by inspection.

Sources:
  - ISO 4217 minor units: https://www.iso.org/iso-4217-currency-codes.html
  - decimal.ROUND_HALF_EVEN:
    https://docs.python.org/3/library/decimal.html#decimal.ROUND_HALF_EVEN
"""

import pytest

import impl

# The "exponent" column of ISO 4217 for the codes the ticket names.
EXPONENTS = {
    "USD": 2,
    "EUR": 2,
    "JPY": 0,
    "ISK": 0,
    "UGX": 0,
    "KWD": 3,
    "BHD": 3,
    "OMR": 3,
    "TND": 3,
    "CLF": 4,
}


def fmt(amount, currency="USD"):
    return impl.format_amount(amount, currency, EXPONENTS)


def test_half_even_rounds_a_tie_up_when_the_kept_digit_is_odd():
    """ROUND_HALF_EVEN, and the first row of the ticket's rounding table."""
    assert fmt("2.675") == "2.68"


def test_half_even_rounds_a_tie_down_when_the_kept_digit_is_even():
    """ROUND_HALF_EVEN: this is where half-even parts company with half-up."""
    assert fmt("2.665") == "2.66"


def test_tie_survives_because_the_value_comes_from_the_string():
    """Ticket: build with Decimal(amount); float('8.835') is below the tie."""
    assert fmt("8.835") == "8.84"


def test_negative_ties_are_symmetric_and_keep_the_sign():
    """Ticket: 'negatives behave symmetrically and keep their sign'."""
    assert fmt("-2.675") == "-2.68"
    assert fmt("-0.125") == "-0.12"


def test_jpy_has_zero_minor_units():
    """ISO 4217 gives JPY exponent 0, and 4 is already even."""
    assert fmt("1234.5", "JPY") == "1234"


def test_zero_exponent_emits_no_decimal_point():
    """Ticket: 'no decimal point at all' -- never '1236.' and never '1236.0'."""
    result = fmt("1235.5", "JPY")
    assert result == "1236"
    assert "." not in result


def test_kwd_has_three_minor_units():
    """ISO 4217 gives KWD exponent 3; the tie keeps the even digit 4."""
    assert fmt("1.2345", "KWD") == "1.234"


def test_bhd_has_three_minor_units():
    """ISO 4217 gives BHD exponent 3; hard-coding 2 would give '2.00'."""
    assert fmt("2.0005", "BHD") == "2.000"


def test_clf_has_four_minor_units():
    """ISO 4217 gives CLF exponent 4; the tie keeps the even digit 4."""
    assert fmt("0.12345", "CLF") == "0.1234"


def test_scientific_notation_is_accepted():
    """Ticket: any string decimal.Decimal accepts as a finite number."""
    assert fmt("1E+2") == "100.00"
    assert fmt("-1.5e-3") == "0.00"


def test_fewer_decimals_than_the_target_are_zero_padded():
    """Ticket: 'exactly `exponent` digits after the point'."""
    assert fmt("5") == "5.00"
    assert fmt("1.5", "KWD") == "1.500"


def test_negative_amount_that_rounds_to_zero_loses_its_sign():
    """Ticket: '-0.004' in USD is '0.00', not '-0.00'."""
    assert fmt("-0.004") == "0.00"
    assert fmt("-0.4", "JPY") == "0"


def test_no_thousands_separator_and_no_exponent_notation():
    """Ticket: 'plain positional decimal string', no grouping."""
    assert fmt("1234567.891") == "1234567.89"
    assert fmt("1E+9") == "1000000000.00"


def test_leading_plus_is_dropped():
    """Ticket: 'no leading +' -- '+1.5' in USD is '1.50'."""
    assert fmt("+1.5") == "1.50"


def test_surrounding_whitespace_is_accepted():
    """Ticket: '  1.5  ' is valid because decimal.Decimal accepts it."""
    assert fmt("  1.5  ") == "1.50"


def test_unknown_currency_raises_key_error():
    """Ticket: 'If currency is not a key of exponents, raise KeyError'."""
    with pytest.raises(KeyError):
        fmt("1.00", "XYZ")


def test_currency_lookup_is_case_sensitive():
    """Ticket: 'Look the code up exactly as given: no upper-casing'."""
    with pytest.raises(KeyError):
        fmt("1.00", "usd")


def test_currency_is_checked_before_the_amount():
    """Ticket: unknown code plus bad amount raises KeyError, not ValueError."""
    with pytest.raises(KeyError):
        fmt("not-a-number", "XYZ")


@pytest.mark.parametrize(
    "bad", ["", "abc", "1.2.3", "12,34", "$1.00", "1 000.00", "--1", "1,234.56"]
)
def test_malformed_amount_raises_value_error(bad):
    """Ticket: decimal.InvalidOperation must be translated to ValueError."""
    with pytest.raises(ValueError):
        fmt(bad)


@pytest.mark.parametrize("bad", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_non_finite_amounts_raise_value_error(bad):
    """Ticket: these parse as Decimal but are not finite, so not valid money."""
    with pytest.raises(ValueError):
        fmt(bad)
