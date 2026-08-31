import impl
import pytest


# Basic functionality tests

def test_no_discounts():
    """Empty discount list returns normalized subtotal."""
    assert impl.apply_discounts("100.00", []) == "100.00"


def test_single_percent_discount():
    """Single percentage discount applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "20"}]) == "80.00"


def test_single_amount_discount():
    """Single amount discount applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "30.00"}]) == "70.00"


def test_stacked_discounts_compound():
    """Stacked discounts apply to remaining balance (worked example)."""
    result = impl.apply_discounts(
        "100.00",
        [
            {"kind": "percent", "value": "20"},
            {"kind": "amount", "value": "5.00"},
            {"kind": "percent", "value": "10"}
        ]
    )
    assert result == "67.50"


def test_discount_order_matters():
    """Same discounts in different order give different result."""
    result = impl.apply_discounts(
        "100.00",
        [
            {"kind": "amount", "value": "5.00"},
            {"kind": "percent", "value": "20"},
            {"kind": "percent", "value": "10"}
        ]
    )
    assert result == "68.40"


# Normalization and rounding tests

def test_subtotal_normalization():
    """Subtotal with fewer than 2 decimals normalized to exactly 2."""
    assert impl.apply_discounts("100.1", []) == "100.10"
    assert impl.apply_discounts("100", []) == "100.00"


def test_banker_rounding():
    """Rounding uses ROUND_HALF_EVEN (half to even)."""
    # 10.05 * 50% = 5.025 -> 5.02 (2 is even)
    assert impl.apply_discounts("10.05", [{"kind": "percent", "value": "50"}]) == "5.02"
    # 10.15 * 50% = 5.075 -> 5.08 (8 is even)
    assert impl.apply_discounts("10.15", [{"kind": "percent", "value": "50"}]) == "5.08"


# Edge cases

def test_zero_subtotal_unchanged():
    """Zero subtotal remains zero."""
    assert impl.apply_discounts("0.00", [{"kind": "percent", "value": "50"}]) == "0.00"


def test_percent_100_discount():
    """100% discount reduces to zero."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "100"}]) == "0.00"


def test_clamping_at_zero():
    """Amount discount larger than total clamps to zero."""
    assert impl.apply_discounts("10.00", [{"kind": "amount", "value": "20.00"}]) == "0.00"


def test_clamping_stops_effect_of_subsequent_discounts():
    """After clamping to zero, subsequent discounts have no effect."""
    result = impl.apply_discounts(
        "10.00",
        [
            {"kind": "amount", "value": "20.00"},
            {"kind": "percent", "value": "50"}
        ]
    )
    assert result == "0.00"


# Error validation tests

def test_error_invalid_subtotal_type():
    """ValueError raised for non-string subtotal."""
    with pytest.raises(ValueError):
        impl.apply_discounts(100, [])


def test_error_invalid_subtotal_format():
    """ValueError raised for malformed subtotal."""
    with pytest.raises(ValueError):
        impl.apply_discounts("+100.00", [])
    with pytest.raises(ValueError):
        impl.apply_discounts("-100.00", [])


def test_error_discount_structure():
    """ValueError raised for malformed discount structure."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", ["not_a_dict"])
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent"}])  # missing value
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"value": "20"}])  # missing kind


def test_error_invalid_kind():
    """ValueError raised for invalid discount kind."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "invalid", "value": "20"}])


def test_error_invalid_discount_value():
    """ValueError raised for invalid or malformed discount value."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": 20}])  # not string
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "abc"}])  # malformed
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "-20"}])  # negative


def test_error_percent_exceeds_100():
    """ValueError raised when percent discount exceeds 100."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "101"}])


def test_error_validation_after_clamping():
    """ValueError raised for invalid discount even after clamping to zero."""
    with pytest.raises(ValueError):
        impl.apply_discounts(
            "100.00",
            [
                {"kind": "amount", "value": "200.00"},
                {"kind": "percent", "value": "110"}
            ]
        )


def test_pure_function_no_mutation():
    """Function does not mutate input."""
    discounts = [{"kind": "percent", "value": "20"}]
    original = [{"kind": "percent", "value": "20"}]
    impl.apply_discounts("100.00", discounts)
    assert discounts == original
