import pytest
import impl


def test_empty_discounts():
    """Empty discount list returns normalized subtotal."""
    assert impl.apply_discounts("100.00", []) == "100.00"
    assert impl.apply_discounts("100.5", []) == "100.50"
    assert impl.apply_discounts("100", []) == "100.00"


def test_single_percent_discount():
    """Single percent discount is applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "20"}]) == "80.00"


def test_single_amount_discount():
    """Single amount discount is applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "5.00"}]) == "95.00"


def test_stacked_discounts_order_matters():
    """Order of discounts affects the result - they compound."""
    # 100 * 0.8 = 80, 80 - 5 = 75, 75 * 0.9 = 67.50
    result1 = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "10"}
    ])
    assert result1 == "67.50"
    
    # 100 - 5 = 95, 95 * 0.8 = 76, 76 * 0.9 = 68.40
    result2 = impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "20"},
        {"kind": "percent", "value": "10"}
    ])
    assert result2 == "68.40"


def test_hundred_percent_discount():
    """100% discount results in 0.00."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "100"}]) == "0.00"


def test_amount_exceeds_total_clamped():
    """Amount discount exceeding total is clamped to 0.00."""
    result = impl.apply_discounts("50.00", [{"kind": "amount", "value": "100.00"}])
    assert result == "0.00"


def test_subtotal_normalization():
    """Subtotal is normalized to exactly two decimal places."""
    assert impl.apply_discounts("100", []) == "100.00"
    assert impl.apply_discounts("100.5", []) == "100.50"
    assert impl.apply_discounts("100.555", []) == "100.56"


def test_zero_and_negative_zero():
    """Zero and negative zero are handled correctly."""
    assert impl.apply_discounts("0.00", []) == "0.00"
    assert impl.apply_discounts("0", []) == "0.00"
    assert impl.apply_discounts("-0.00", []) == "0.00"


def test_decimal_values():
    """Decimal values in discounts work correctly."""
    # Percent: 100 * (100 - 12.5) / 100 = 87.50
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "12.5"}]) == "87.50"
    # Amount: 100 - 5.99 = 94.01
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "5.99"}]) == "94.01"


def test_subtotal_validation_errors():
    """Subtotal validation errors are raised."""
    with pytest.raises(ValueError):
        impl.apply_discounts(123, [])  # not a string
    with pytest.raises(ValueError):
        impl.apply_discounts("+100.00", [])  # plus sign
    with pytest.raises(ValueError):
        impl.apply_discounts("5.", [])  # bare decimal
    with pytest.raises(ValueError):
        impl.apply_discounts(".5", [])  # bare decimal
    with pytest.raises(ValueError):
        impl.apply_discounts("", [])  # empty
    with pytest.raises(ValueError):
        impl.apply_discounts("-100.00", [])  # negative


def test_discount_structure_validation():
    """Discount structure validation errors are raised."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", ["not a dict"])  # not a dict
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"value": "20"}])  # missing kind
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent"}])  # missing value


def test_discount_kind_validation():
    """Discount kind must be exactly 'percent' or 'amount'."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "invalid", "value": "20"}])


def test_discount_value_validation():
    """Discount value validation errors are raised."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": 20}])  # not a string
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "abc"}])  # invalid format
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "-20"}])  # negative


def test_percent_discount_constraints():
    """Percent discount cannot exceed 100."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "101"}])


def test_amount_discount_no_upper_bound():
    """Amount discount can exceed 100 (gets clamped to 0)."""
    result = impl.apply_discounts("100.00", [{"kind": "amount", "value": "150"}])
    assert result == "0.00"


def test_small_and_large_amounts():
    """Small and large amounts are handled correctly."""
    assert impl.apply_discounts("0.01", []) == "0.01"
    assert impl.apply_discounts("999999.99", []) == "999999.99"


def test_zero_discounts():
    """Zero-value discounts leave amount unchanged."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "0"}]) == "100.00"
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "0"}]) == "100.00"


def test_discounts_not_mutated():
    """The discounts list is not mutated by the function."""
    discounts = [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"}
    ]
    original = [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"}
    ]
    impl.apply_discounts("100.00", discounts)
    assert discounts == original
