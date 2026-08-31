import impl
import pytest

# === NORMAL CASES ===

def test_empty_discounts():
    """No discounts returns normalized subtotal."""
    assert impl.apply_discounts("100.00", []) == "100.00"

def test_single_percent_discount():
    """Single percentage discount."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "20"}]) == "80.00"

def test_single_amount_discount():
    """Single amount discount."""
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "30"}]) == "70.00"

def test_stacked_discounts_example_one():
    """20% → -5.00 → 10% on 100.00 yields 67.50 (compounding, not additive)."""
    result = impl.apply_discounts("100.00", [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "10"}
    ])
    assert result == "67.50"

def test_stacked_discounts_example_two():
    """-5.00 → 20% → 10% on 100.00 yields 68.40 (order matters)."""
    result = impl.apply_discounts("100.00", [
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "20"},
        {"kind": "percent", "value": "10"}
    ])
    assert result == "68.40"

def test_discount_to_zero():
    """Amount discount exactly equals remaining total."""
    assert impl.apply_discounts("50.00", [{"kind": "amount", "value": "50.00"}]) == "0.00"

def test_discount_exceeds_total():
    """Amount discount larger than remaining total is clamped to 0.00."""
    assert impl.apply_discounts("50.00", [{"kind": "amount", "value": "100.00"}]) == "0.00"

def test_percent_discount_100():
    """100% discount is allowed."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "100"}]) == "0.00"

def test_subtotal_normalization():
    """Subtotal with >2 decimals normalized to exactly 2 with ROUND_HALF_EVEN."""
    assert impl.apply_discounts("100.456", []) == "100.46"
    assert impl.apply_discounts("100.1", []) == "100.10"

def test_negative_zero_is_zero():
    """-0.00 is accepted and treated as 0.00."""
    assert impl.apply_discounts("-0.00", []) == "0.00"

# === ERROR CASES ===

def test_error_subtotal_type_and_format():
    """Subtotal must be a string and match decimal grammar."""
    # Not a string
    with pytest.raises(ValueError):
        impl.apply_discounts(100.00, [])
    
    # Malformed: plus sign
    with pytest.raises(ValueError) as exc:
        impl.apply_discounts("+100.00", [])
    assert "+100.00" in str(exc.value)
    
    # Malformed: trailing dot
    with pytest.raises(ValueError) as exc:
        impl.apply_discounts("100.", [])
    assert "100." in str(exc.value)

def test_error_subtotal_negative():
    """Negative subtotal raises ValueError."""
    with pytest.raises(ValueError) as exc:
        impl.apply_discounts("-50.00", [])
    assert "-50.00" in str(exc.value)

def test_error_discount_structure():
    """Discount must be a dict with 'kind' and 'value' keys."""
    # Not a dict
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", ["not a dict"])
    
    # Missing 'kind'
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"value": "20"}])
    
    # Missing 'value'
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent"}])

def test_error_invalid_kind():
    """'kind' must be exactly 'percent' or 'amount'."""
    with pytest.raises(ValueError) as exc:
        impl.apply_discounts("100.00", [{"kind": "invalid", "value": "20"}])
    assert "invalid" in str(exc.value)

def test_error_value_type_and_format():
    """'value' must be a string and match decimal grammar."""
    # Not a string
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": 20}])
    
    # Malformed
    with pytest.raises(ValueError) as exc:
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "20%"}])
    assert "20%" in str(exc.value)

def test_error_value_negative():
    """'value' cannot be negative for either kind."""
    # Negative percent
    with pytest.raises(ValueError) as exc:
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "-10"}])
    assert "-10" in str(exc.value)
    
    # Negative amount
    with pytest.raises(ValueError) as exc:
        impl.apply_discounts("100.00", [{"kind": "amount", "value": "-5.00"}])
    assert "-5.00" in str(exc.value)

def test_error_percent_exceeds_100():
    """For percent, value must not exceed 100."""
    with pytest.raises(ValueError) as exc:
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "101"}])
    assert "101" in str(exc.value)

def test_error_validation_per_discount():
    """Each discount is validated when reached, not pre-validated."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [
            {"kind": "percent", "value": "20"},
            {"kind": "percent", "value": "105"}
        ])
