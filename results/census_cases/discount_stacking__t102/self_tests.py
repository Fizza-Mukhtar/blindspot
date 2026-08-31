import pytest
import impl

def test_empty_discounts():
    """Empty discounts list returns normalized subtotal."""
    assert impl.apply_discounts("100.00", []) == "100.00"
    assert impl.apply_discounts("100", []) == "100.00"
    assert impl.apply_discounts("100.5", []) == "100.50"

def test_single_percentage_discount():
    """Single percentage discount applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "20"}]) == "80.00"
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "100"}]) == "0.00"

def test_single_amount_discount():
    """Single fixed amount discount applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "5.00"}]) == "95.00"

def test_compound_percentages():
    """Percentages compound on remaining amount, not added together."""
    # 20% off €100 = €80, then 10% off €80 = €72 (not 70)
    assert impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "percent", "value": "10"}
    ]) == "72.00"

def test_mixed_discounts_order_matters():
    """Discount order affects final result due to compounding."""
    # €100 with 20%, then €5 → €75, then 10% → €67.50
    result1 = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "10"}
    ])
    assert result1 == "67.50"
    
    # €100 with €5 → €95, then 20% → €76, then 10% → €68.40
    result2 = impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "20"},
        {"kind": "percent", "value": "10"}
    ])
    assert result2 == "68.40"

def test_zero_subtotal():
    """Zero subtotal remains zero after discounts."""
    assert impl.apply_discounts("0.00", [{"kind": "percent", "value": "20"}]) == "0.00"
    assert impl.apply_discounts("0.00", [{"kind": "amount", "value": "5.00"}]) == "0.00"

def test_negative_zero_input():
    """Negative zero is treated as zero."""
    assert impl.apply_discounts("-0.00", []) == "0.00"

def test_subtotal_quantization_and_formatting():
    """Subtotal quantized to exactly 2 decimal places."""
    assert impl.apply_discounts("100.123", []) == "100.12"
    assert impl.apply_discounts("100.1", []) == "100.10"
    assert impl.apply_discounts("100", []) == "100.00"

def test_amount_discount_clamp():
    """Amount discount larger than running total clamps to 0."""
    assert impl.apply_discounts("10.00", [{"kind": "amount", "value": "20.00"}]) == "0.00"

def test_discounts_on_clamped_zero():
    """Further discounts on zero running total don't change it."""
    assert impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "100.00"},
        {"kind": "percent", "value": "50"},
        {"kind": "amount", "value": "10.00"}
    ]) == "0.00"

def test_rounding_half_even():
    """Intermediate results rounded with ROUND_HALF_EVEN."""
    assert impl.apply_discounts("50.33", [{"kind": "percent", "value": "10"}]) == "45.30"

def test_multiple_amount_discounts():
    """Multiple amount discounts stack correctly."""
    assert impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "10.00"},
        {"kind": "amount", "value": "20.00"}
    ]) == "70.00"

def test_error_subtotal_type():
    """ValueError raised when subtotal is not a string."""
    with pytest.raises(ValueError):
        impl.apply_discounts(100, [])
    with pytest.raises(ValueError):
        impl.apply_discounts(100.0, [])

def test_error_subtotal_malformed():
    """ValueError raised for malformed subtotal strings."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00.00", [])
    with pytest.raises(ValueError):
        impl.apply_discounts("5.", [])
    with pytest.raises(ValueError):
        impl.apply_discounts(".5", [])
    with pytest.raises(ValueError):
        impl.apply_discounts("", [])

def test_error_subtotal_negative():
    """ValueError raised when subtotal is negative."""
    with pytest.raises(ValueError):
        impl.apply_discounts("-100.00", [])

def test_error_discount_structure():
    """ValueError raised for invalid discount structure."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", ["string not dict"])
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"value": "10"}])  # missing kind
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent"}])  # missing value

def test_error_invalid_kind():
    """ValueError raised for kind not 'percent' or 'amount'."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "discount", "value": "10"}])

def test_error_value_type_and_format():
    """ValueError raised for non-string or malformed value."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": 10}])
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "amount", "value": "10.00.00"}])

def test_error_negative_value():
    """ValueError raised for negative discount values."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "-10"}])
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "amount", "value": "-5.00"}])

def test_error_percent_exceeds_100():
    """ValueError raised for percent discount exceeding 100."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "101"}])
