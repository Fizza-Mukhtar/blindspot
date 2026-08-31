import pytest
import impl


def test_worked_example():
    """Test the exact example from PRICING-2317."""
    result = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "10"}
    ])
    assert result == "67.50"


def test_empty_discounts_list():
    """Empty discount list returns normalized subtotal."""
    assert impl.apply_discounts("100", []) == "100.00"
    assert impl.apply_discounts("100.5", []) == "100.50"
    assert impl.apply_discounts("100.123", []) == "100.12"


def test_single_percent_discount():
    """Single percent discount applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "20"}]) == "80.00"
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "50"}]) == "50.00"
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "0"}]) == "100.00"


def test_single_amount_discount():
    """Single amount discount applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "20"}]) == "80.00"
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "5.50"}]) == "94.50"
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "0"}]) == "100.00"


def test_compounding_percentages():
    """Percentages compound (multiply), not add."""
    # 20% then 10%: 100 × 0.8 × 0.9 = 72, not 100 × 0.7 = 70
    result = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "percent", "value": "10"}
    ])
    assert result == "72.00"


def test_order_of_discounts_matters():
    """Order of discounts affects the final result."""
    # Percent first, then amount: 100 × 0.8 - 5 = 75
    pct_then_amt = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"}
    ])
    assert pct_then_amt == "75.00"
    
    # Amount first, then percent: (100 - 5) × 0.8 = 76
    amt_then_pct = impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "20"}
    ])
    assert amt_then_pct == "76.00"


def test_amount_discount_clamps_at_zero():
    """Amount discount cannot take running total below zero."""
    result = impl.apply_discounts("10.00", [{"kind": "amount", "value": "15.00"}])
    assert result == "0.00"


def test_discounts_after_clamp_operate_on_zero():
    """Discounts after clamping at zero operate on zero."""
    result = impl.apply_discounts("10.00", [
        {"kind": "amount", "value": "20.00"},
        {"kind": "percent", "value": "50"},
        {"kind": "amount", "value": "10"}
    ])
    assert result == "0.00"


def test_percent_100_discount():
    """100% discount removes everything."""
    result = impl.apply_discounts("100.00", [{"kind": "percent", "value": "100"}])
    assert result == "0.00"


def test_zero_subtotal():
    """Zero subtotal stays zero."""
    assert impl.apply_discounts("0", []) == "0.00"
    assert impl.apply_discounts("0.00", [{"kind": "percent", "value": "50"}, {"kind": "amount", "value": "10"}]) == "0.00"


def test_banker_rounding_half_even():
    """Banker's rounding: .5 goes to nearest even digit."""
    # 5.025 rounds to 5.02 (2 is even)
    assert impl.apply_discounts("5.025", []) == "5.02"
    # 5.075 rounds to 5.08 (8 is even)
    assert impl.apply_discounts("5.075", []) == "5.08"
    # 5.035 rounds to 5.04 (4 is even)
    assert impl.apply_discounts("5.035", []) == "5.04"


def test_rounding_after_each_step():
    """Rounding happens after each discount, not just at the end."""
    # 10 * (100-33.33)/100 = 6.667... which rounds to 6.67
    result = impl.apply_discounts("10.00", [{"kind": "percent", "value": "33.33"}])
    assert result == "6.67"


def test_error_subtotal_not_string():
    """ValueError if subtotal is not a string."""
    with pytest.raises(ValueError, match="subtotal is not a str"):
        impl.apply_discounts(100.00, [])
    with pytest.raises(ValueError, match="subtotal is not a str"):
        impl.apply_discounts(100, [])


def test_error_subtotal_malformed():
    """ValueError if subtotal doesn't match grammar."""
    with pytest.raises(ValueError, match="subtotal is malformed"):
        impl.apply_discounts("", [])
    with pytest.raises(ValueError, match="subtotal is malformed"):
        impl.apply_discounts("abc", [])
    with pytest.raises(ValueError, match="subtotal is malformed"):
        impl.apply_discounts("+100", [])
    with pytest.raises(ValueError, match="subtotal is malformed"):
        impl.apply_discounts("100,000", [])
    with pytest.raises(ValueError, match="subtotal is malformed"):
        impl.apply_discounts(".5", [])


def test_error_subtotal_negative():
    """ValueError if subtotal is negative."""
    with pytest.raises(ValueError, match="subtotal is negative: -50"):
        impl.apply_discounts("-50", [])
    with pytest.raises(ValueError, match="subtotal is negative: -0.01"):
        impl.apply_discounts("-0.01", [])


def test_error_discount_not_dict():
    """ValueError if discount is not a dict."""
    with pytest.raises(ValueError, match="discount is not a mapping"):
        impl.apply_discounts("100", ["not a dict"])
    with pytest.raises(ValueError, match="discount is not a mapping"):
        impl.apply_discounts("100", [None])


def test_error_discount_missing_kind_or_value():
    """ValueError if discount missing 'kind' or 'value'."""
    with pytest.raises(ValueError, match="discount is missing 'kind'"):
        impl.apply_discounts("100", [{"value": "20"}])
    with pytest.raises(ValueError, match="discount is missing 'value'"):
        impl.apply_discounts("100", [{"kind": "percent"}])


def test_error_invalid_kind():
    """ValueError if kind is not 'percent' or 'amount'."""
    with pytest.raises(ValueError, match="kind is invalid"):
        impl.apply_discounts("100", [{"kind": "invalid", "value": "20"}])
    with pytest.raises(ValueError, match="kind is invalid"):
        impl.apply_discounts("100", [{"kind": "Percent", "value": "20"}])


def test_error_value_not_string():
    """ValueError if value is not a string."""
    with pytest.raises(ValueError, match="value is not a str"):
        impl.apply_discounts("100", [{"kind": "percent", "value": 20}])
    with pytest.raises(ValueError, match="value is not a str"):
        impl.apply_discounts("100", [{"kind": "amount", "value": 5.00}])


def test_error_value_malformed():
    """ValueError if value doesn't match grammar."""
    with pytest.raises(ValueError, match="value is malformed"):
        impl.apply_discounts("100", [{"kind": "percent", "value": ""}])
    with pytest.raises(ValueError, match="value is malformed"):
        impl.apply_discounts("100", [{"kind": "percent", "value": "+20"}])
    with pytest.raises(ValueError, match="value is malformed"):
        impl.apply_discounts("100", [{"kind": "amount", "value": "abc"}])


def test_error_value_negative():
    """ValueError if discount value is negative."""
    with pytest.raises(ValueError, match="value is negative: -20"):
        impl.apply_discounts("100", [{"kind": "percent", "value": "-20"}])
    with pytest.raises(ValueError, match="value is negative: -5.00"):
        impl.apply_discounts("100", [{"kind": "amount", "value": "-5.00"}])


def test_error_percent_greater_than_100():
    """ValueError if percent discount is greater than 100."""
    with pytest.raises(ValueError, match="percent value is greater than 100: 101"):
        impl.apply_discounts("100", [{"kind": "percent", "value": "101"}])
    with pytest.raises(ValueError, match="percent value is greater than 100: 200.5"):
        impl.apply_discounts("100", [{"kind": "percent", "value": "200.5"}])


def test_error_validation_even_if_zero_clamped():
    """Discount validation happens even if running total is clamped to zero."""
    # Percent > 100 should raise even though the previous discount clamped to 0
    with pytest.raises(ValueError, match="percent value is greater than 100"):
        impl.apply_discounts("100", [
            {"kind": "amount", "value": "100"},
            {"kind": "percent", "value": "101"}
        ])
