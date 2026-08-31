"""Tests for impl.apply_discounts (PRICING-2317)."""

import copy

import pytest

import impl


def test_worked_example_order_percent_amount_percent():
    result = impl.apply_discounts(
        "100.00",
        [
            {"kind": "percent", "value": "20"},
            {"kind": "amount", "value": "5.00"},
            {"kind": "percent", "value": "10"},
        ],
    )
    assert result == "67.50"


def test_worked_example_order_amount_percent_percent():
    result = impl.apply_discounts(
        "100.00",
        [
            {"kind": "amount", "value": "5.00"},
            {"kind": "percent", "value": "20"},
            {"kind": "percent", "value": "10"},
        ],
    )
    assert result == "68.40"


def test_empty_discounts_returns_normalized_subtotal():
    assert impl.apply_discounts("42", []) == "42.00"
    assert impl.apply_discounts("42.1", []) == "42.10"


def test_subtotal_rounding_uses_banker_rounding():
    # Exact halves round to the nearest even last digit.
    assert impl.apply_discounts("5.025", []) == "5.02"
    assert impl.apply_discounts("5.075", []) == "5.08"


def test_step_rounding_uses_banker_rounding_each_step():
    # 25.00 -> (50% off) -> 12.50 -> (1% off) -> 12.375 -> rounds half-even to 12.38
    result = impl.apply_discounts(
        "25.00",
        [
            {"kind": "percent", "value": "50"},
            {"kind": "percent", "value": "1"},
        ],
    )
    assert result == "12.38"


def test_clamp_at_zero_and_subsequent_discounts_stay_zero():
    # 10.00 - 15.00 clamps to 0.00, then a further 50% off leaves it at 0.00.
    result = impl.apply_discounts(
        "10.00",
        [
            {"kind": "amount", "value": "15.00"},
            {"kind": "percent", "value": "50"},
        ],
    )
    assert result == "0.00"


def test_negative_zero_normalized_to_positive_zero():
    assert impl.apply_discounts("-0.00", []) == "0.00"
    assert impl.apply_discounts("-0", [{"kind": "amount", "value": "0"}]) == "0.00"


def test_validation_still_raises_after_clamp_to_zero():
    with pytest.raises(ValueError) as exc_info:
        impl.apply_discounts(
            "5.00",
            [
                {"kind": "amount", "value": "10.00"},
                {"kind": "percent", "value": "150"},
            ],
        )
    assert "150" in str(exc_info.value)


def test_purity_does_not_mutate_discounts_or_subtotal():
    discounts = [
        {"kind": "percent", "value": "20"},
        {"kind": "amount", "value": "5.00"},
    ]
    snapshot = copy.deepcopy(discounts)

    result = impl.apply_discounts("100.00", discounts)

    assert result == "75.00"
    assert discounts == snapshot


def test_amount_discount_can_exceed_subtotal_with_no_upper_bound():
    result = impl.apply_discounts("10.00", [{"kind": "amount", "value": "999999.99"}])
    assert result == "0.00"


def test_percent_value_of_100_is_allowed():
    result = impl.apply_discounts("50.00", [{"kind": "percent", "value": "100"}])
    assert result == "0.00"


@pytest.mark.parametrize(
    "bad_subtotal",
    [
        123,
        None,
        12.5,
        "",
        "abc",
        "1,000",
        "+5",
        "5.",
        ".5",
        "1e5",
        "-1.00",
        "-0.01",
    ],
)
def test_subtotal_errors(bad_subtotal):
    with pytest.raises(ValueError) as exc_info:
        impl.apply_discounts(bad_subtotal, [])
    assert repr(bad_subtotal) in str(exc_info.value)


@pytest.mark.parametrize(
    "bad_discount",
    [
        "not-a-mapping",
        42,
        {"value": "10"},
        {"kind": "amount"},
    ],
)
def test_discount_structure_errors(bad_discount):
    with pytest.raises(ValueError) as exc_info:
        impl.apply_discounts("100.00", [bad_discount])
    assert repr(bad_discount) in str(exc_info.value)


def test_discount_kind_invalid_raises():
    with pytest.raises(ValueError) as exc_info:
        impl.apply_discounts("100.00", [{"kind": "BOGO", "value": "10"}])
    assert "BOGO" in str(exc_info.value)


@pytest.mark.parametrize(
    "bad_value",
    ["abc", "-5", "-5.00", "", "1,0", "+1", "5.", 10],
)
def test_discount_value_errors(bad_value):
    with pytest.raises(ValueError) as exc_info:
        impl.apply_discounts("100.00", [{"kind": "amount", "value": bad_value}])
    assert repr(bad_value) in str(exc_info.value)


def test_percent_value_exceeds_100_raises():
    with pytest.raises(ValueError) as exc_info:
        impl.apply_discounts("100.00", [{"kind": "percent", "value": "150"}])
    assert "150" in str(exc_info.value)
