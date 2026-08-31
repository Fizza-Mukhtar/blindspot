import impl
import pytest


# Normal path tests
def test_empty_discounts_list():
    """Empty discounts list returns normalized subtotal."""
    assert impl.apply_discounts("100.00", []) == "100.00"
    assert impl.apply_discounts("100", []) == "100.00"


def test_single_percent_discount():
    """Single percent discount is applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "20"}]) == "80.00"


def test_single_amount_discount():
    """Single amount discount is applied correctly."""
    assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "5.00"}]) == "95.00"


def test_multiple_discounts_stacking():
    """Multiple discounts compound correctly per ticket example."""
    discounts = [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "10"}
    ]
    # 100 -> 80 -> 75 -> 67.50
    assert impl.apply_discounts("100.00", discounts) == "67.50"


def test_discount_order_matters():
    """Same discounts in different order produce different results."""
    discounts1 = [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "10"}
    ]
    discounts2 = [
        {"kind": "amount", "value": "5.00"},
        {"kind": "percent", "value": "20"},
        {"kind": "percent", "value": "10"}
    ]
    assert impl.apply_discounts("100.00", discounts1) == "67.50"
    assert impl.apply_discounts("100.00", discounts2) == "68.40"


# Edge cases
def test_zero_percent_discount():
    """0% discount leaves amount unchanged."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "0"}]) == "100.00"


def test_100_percent_discount():
    """100% discount takes everything to 0.00."""
    assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "100"}]) == "0.00"


def test_amount_discount_exceeds_total():
    """Discount larger than running total clamps to 0.00."""
    assert impl.apply_discounts("50.00", [{"kind": "amount", "value": "60.00"}]) == "0.00"


def test_negative_zero_normalized():
    """Negative zero is accepted and normalized to 0.00."""
    assert impl.apply_discounts("-0.00", []) == "0.00"


def test_subtotal_quantization():
    """Subtotal with many decimals is quantized correctly."""
    assert impl.apply_discounts("100.556", []) == "100.56"


def test_subtotal_no_decimal_point():
    """Subtotal without decimal point is normalized."""
    assert impl.apply_discounts("100", []) == "100.00"


def test_rounding_intermediate_results():
    """Intermediate results are quantized with ROUND_HALF_EVEN."""
    # 10 * (100 - 33.33) / 100 = 6.667... rounds to 6.67
    assert impl.apply_discounts("10.00", [{"kind": "percent", "value": "33.33"}]) == "6.67"


# Validation error tests
def test_subtotal_not_string():
    """Non-string subtotal raises ValueError."""
    with pytest.raises(ValueError):
        impl.apply_discounts(100, [])


def test_subtotal_malformed():
    """Malformed subtotal raises ValueError."""
    with pytest.raises(ValueError):
        impl.apply_discounts(".50", [])


def test_subtotal_negative():
    """Negative subtotal raises ValueError."""
    with pytest.raises(ValueError):
        impl.apply_discounts("-100.00", [])


def test_discount_not_mapping():
    """Non-dict discount raises ValueError."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", ["not a dict"])


def test_discount_missing_keys():
    """Discount missing required keys raises ValueError."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"value": "20"}])
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent"}])


def test_discount_invalid_kind():
    """Invalid discount kind raises ValueError."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "invalid", "value": "20"}])


def test_discount_value_invalid():
    """Invalid discount value raises ValueError."""
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "20."}])
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "-20"}])
    with pytest.raises(ValueError):
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "101"}])


def test_does_not_mutate_inputs():
    """Function does not mutate discounts list or dicts."""
    discount_dict = {"kind": "percent", "value": "20"}
    discounts = [discount_dict]
    impl.apply_discounts("100.00", discounts)
    assert discount_dict == {"kind": "percent", "value": "20"}
    assert discounts == [discount_dict]
