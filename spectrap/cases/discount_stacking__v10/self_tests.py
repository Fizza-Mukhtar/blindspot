import pytest
import impl


# === Normal functionality ===

def test_worked_example():
    """Test the worked example from the ticket."""
    result = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "10"}
    ])
    assert result == "67.50"


def test_empty_discount_list():
    """Empty discount list returns normalized subtotal."""
    assert impl.apply_discounts("100.00", []) == "100.00"
    assert impl.apply_discounts("100", []) == "100.00"
    assert impl.apply_discounts("100.1", []) == "100.10"


def test_single_percent_discount():
    """Apply single percent discount."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "20"}]) == "80.00"
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "50"}]) == "50.00"


def test_single_amount_discount():
    """Apply single amount discount."""
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "25.00"}]) == "75.00"
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "10"}]) == "90.00"


def test_multiple_percents_compound():
    """Multiple percent discounts compound, not add."""
    # 20% off 100 = 80, then 10% off 80 = 72
    # NOT (100 - 100*0.20 - 100*0.10) = 70
    result = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "percent", "value": "10"}
    ])
    assert result == "72.00"


def test_amount_and_percent_stacking():
    """Amount and percent discounts stack correctly."""
    # Different order gives different results
    result1 = impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "20"}
    ])
    # (100 - 5) * 80 / 100 = 95 * 0.8 = 76.00
    assert result1 == "76.00"
    
    result2 = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"}
    ])
    # 100 * 80 / 100 - 5 = 80 - 5 = 75.00
    assert result2 == "75.00"


def test_order_matters():
    """Same three-way stack in different order gives different result."""
    result1 = impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "20"},
        {"kind": "percent", "value": "10"}
    ])
    # 100 - 5 = 95, 95 * 80/100 = 76, 76 * 90/100 = 68.4 -> 68.40
    assert result1 == "68.40"


def test_rounding_at_each_step():
    """Rounding happens after each discount."""
    result = impl.apply_discounts("10.00", [
        {"kind": "percent", "value": "33.33"}
    ])
    # 10.00 * (100 - 33.33) / 100 = 10.00 * 66.67 / 100 = 6.667 -> 6.67
    assert result == "6.67"


def test_banker_rounding():
    """Banker's rounding: half goes to nearest even."""
    # 100.005 should round to 100.00 (0 is even)
    assert impl.apply_discounts("100.005", []) == "100.00"
    # 100.015 should round to 100.02 (2 is even)
    assert impl.apply_discounts("100.015", []) == "100.02"
    # 100.025 should round to 100.02 (2 is even)
    assert impl.apply_discounts("100.025", []) == "100.02"
    # 100.035 should round to 100.04 (4 is even)
    assert impl.apply_discounts("100.035", []) == "100.04"


def test_clamp_at_zero():
    """Running total clamped at zero."""
    assert impl.apply_discounts("10.00", [{"kind": "amount", "value": "20.00"}]) == "0.00"
    
    # Multiple amount discounts
    assert impl.apply_discounts("10.00", [
        {"kind": "amount", "value": "5.00"},
        {"kind": "amount", "value": "10.00"}
    ]) == "0.00"
    
    # Discounts after clamping still operate on 0.00
    assert impl.apply_discounts("10.00", [
        {"kind": "amount", "value": "20.00"},
        {"kind": "percent", "value": "50"}
    ]) == "0.00"


def test_zero_is_positive():
    """Zero returned as '0.00', not '-0.00'."""
    assert impl.apply_discounts("10.00", [{"kind": "amount", "value": "10.00"}]) == "0.00"


def test_fractional_discounts():
    """Fractional percent and amount discounts."""
    assert impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "12.5"}
    ]) == "87.50"
    
    assert impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "5.50"}
    ]) == "94.50"


def test_zero_discounts():
    """Zero discount doesn't change total."""
    assert impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "0"}
    ]) == "100.00"
    
    assert impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "0.00"}
    ]) == "100.00"


# === Error cases ===

def test_subtotal_errors():
    """Subtotal validation errors."""
    # Not a string
    with pytest.raises(ValueError, match="subtotal is not a string"):
        impl.apply_discounts(100.00, [])
    
    # Malformed
    with pytest.raises(ValueError, match="subtotal does not match decimal grammar"):
        impl.apply_discounts("100.00.00", [])
    
    with pytest.raises(ValueError, match="subtotal does not match decimal grammar"):
        impl.apply_discounts("", [])
    
    with pytest.raises(ValueError, match="subtotal does not match decimal grammar"):
        impl.apply_discounts("+100", [])
    
    # Negative
    with pytest.raises(ValueError, match="subtotal is negative"):
        impl.apply_discounts("-10.00", [])


def test_discount_structure_errors():
    """Discount structure validation errors."""
    # Not a mapping
    with pytest.raises(ValueError, match="discount is not a mapping"):
        impl.apply_discounts("100.00", ["invalid"])
    
    # Missing kind
    with pytest.raises(ValueError, match="discount is missing 'kind'"):
        impl.apply_discounts("100.00", [{"value": "10"}])
    
    # Missing value
    with pytest.raises(ValueError, match="discount is missing 'value'"):
        impl.apply_discounts("100.00", [{"kind": "percent"}])


def test_kind_validation_errors():
    """Invalid kind."""
    with pytest.raises(ValueError, match="kind is not 'percent' or 'amount'"):
        impl.apply_discounts("100.00", [{"kind": "invalid", "value": "10"}])
    
    with pytest.raises(ValueError, match="kind is not 'percent' or 'amount'"):
        impl.apply_discounts("100.00", [{"kind": "", "value": "10"}])


def test_discount_value_errors():
    """Discount value validation errors."""
    # Not a string
    with pytest.raises(ValueError, match="discount value is not a string"):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": 20}])
    
    # Malformed
    with pytest.raises(ValueError, match="discount value does not match decimal grammar"):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "20.00.00"}])
    
    # Negative
    with pytest.raises(ValueError, match="discount value is negative"):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "-10"}])
    
    # Percent > 100
    with pytest.raises(ValueError, match="percent discount value is greater than 100"):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "101"}])
    
    # But amount discount can be large
    assert impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "200.00"}
    ]) == "0.00"


def test_validation_in_order():
    """Validation happens as walk reaches each discount."""
    # Valid first discount
    assert impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "50"}
    ]) == "50.00"
    
    # Invalid second discount still raises
    with pytest.raises(ValueError, match="percent discount value is greater than 100"):
        impl.apply_discounts("100.00", [
            {"kind": "percent", "value": "50"},
            {"kind": "percent", "value": "150"}
        ])
    
    # Invalid even if running total clamped
    with pytest.raises(ValueError, match="percent discount value is greater than 100"):
        impl.apply_discounts("10.00", [
            {"kind": "amount", "value": "20.00"},
            {"kind": "percent", "value": "150"}
        ])
