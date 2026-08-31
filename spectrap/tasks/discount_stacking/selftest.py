"""Authoritative examples for PRICING-2317.

Every assertion here traces to the cited authority or to an explicit sentence of
SPEC.md, not to whatever the reference implementation happens to do.
``make verify-corpus`` runs this against ``reference.py`` in CI, which is what
lets the README claim that ground-truth labels are verified by construction
rather than by inspection.

Source: Shopify, "Discount combinations",
https://help.shopify.com/en/manual/discounts/discount-combinations — each
combined discount applies to the amount remaining after the previous one.
"""

import pytest

import impl

PCT = "percent"
AMT = "amount"


def test_percentages_compound_they_do_not_add():
    """The incident in SPEC "Background": 20% then 10% off 100.00 is 72.00.

    Summing the percentages gives 70.00, which is the bug being fixed.
    """
    assert impl.apply_discounts(
        "100.00", [{"kind": PCT, "value": "20"}, {"kind": PCT, "value": "10"}]
    ) == "72.00"


def test_three_percentages_compound():
    """Rule 2: each percent applies to the current running total.

    100 -> 80.00 -> 64.00 -> 51.20.  Adding 20+20+20 would give 40.00.
    """
    assert impl.apply_discounts("100.00", [{"kind": PCT, "value": "20"}] * 3) == "51.20"


def test_worked_example_from_the_ticket():
    """SPEC "Worked example": 100.00, 20%, 5.00 off, 10% -> 67.50."""
    assert impl.apply_discounts(
        "100.00",
        [
            {"kind": PCT, "value": "20"},
            {"kind": AMT, "value": "5.00"},
            {"kind": PCT, "value": "10"},
        ],
    ) == "67.50"


def test_order_of_application_changes_the_result():
    """SPEC "Worked example": "Order matters, and the order is the caller's."

    A percent and an amount that swap places give different totals.
    """
    percent_first = impl.apply_discounts(
        "100.00", [{"kind": PCT, "value": "20"}, {"kind": AMT, "value": "5.00"}]
    )
    amount_first = impl.apply_discounts(
        "100.00", [{"kind": AMT, "value": "5.00"}, {"kind": PCT, "value": "20"}]
    )
    assert percent_first == "75.00"
    assert amount_first == "76.00"
    assert percent_first != amount_first


def test_three_way_stack_reordered():
    """SPEC "Worked example": 5.00 off, then 20%, then 10% -> 68.40."""
    assert impl.apply_discounts(
        "100.00",
        [
            {"kind": AMT, "value": "5.00"},
            {"kind": PCT, "value": "20"},
            {"kind": PCT, "value": "10"},
        ],
    ) == "68.40"


def test_half_even_tie_rounds_down_to_an_even_digit():
    """Rule 3: "5.025 becomes 5.02".  ROUND_HALF_UP would give 5.03."""
    assert impl.apply_discounts("10.05", [{"kind": PCT, "value": "50"}]) == "5.02"


def test_half_even_tie_rounds_up_to_an_even_digit():
    """Rule 3: "5.075 becomes 5.08".  ROUND_HALF_DOWN would give 5.07."""
    assert impl.apply_discounts("10.15", [{"kind": PCT, "value": "50"}]) == "5.08"


def test_rounding_happens_after_every_step_not_once_at_the_end():
    """Rule 3: "a step operates on the rounded output of the step before it".

    1.15 -> 1.035 -> rounds to 1.04 -> 0.936 -> rounds to 0.94.
    Deferring the rounding gives 1.15 x 0.81 = 0.9315 -> 0.93, which is wrong.
    """
    assert impl.apply_discounts(
        "1.15", [{"kind": PCT, "value": "10"}, {"kind": PCT, "value": "10"}]
    ) == "0.94"


def test_amount_step_is_also_rounded_half_even():
    """Rule 3 applied to an amount step: 10.00 - 0.005 = 9.995 -> 10.00."""
    assert impl.apply_discounts("10.00", [{"kind": AMT, "value": "0.005"}]) == "10.00"


def test_fixed_amount_clamps_at_zero():
    """Rule 4: "the running total never goes below zero"."""
    assert impl.apply_discounts("10.00", [{"kind": AMT, "value": "15.00"}]) == "0.00"


def test_discounts_after_a_clamp_operate_on_zero():
    """Rule 4: "Any discounts that follow then operate on a running total of 0.00"."""
    assert impl.apply_discounts(
        "10.00", [{"kind": AMT, "value": "15.00"}, {"kind": PCT, "value": "50"}]
    ) == "0.00"
    assert impl.apply_discounts(
        "10.00", [{"kind": AMT, "value": "15.00"}, {"kind": AMT, "value": "5.00"}]
    ) == "0.00"


def test_hundred_percent_zeroes_the_line():
    """Rule 2 at the boundary the errors section allows: p = 100 is valid."""
    assert impl.apply_discounts(
        "19.99", [{"kind": PCT, "value": "100"}, {"kind": AMT, "value": "1.00"}]
    ) == "0.00"


def test_zero_valued_discounts_leave_the_total_alone():
    """Rule 2 at the other boundary: 0% and 0.00 off are both valid no-ops."""
    assert impl.apply_discounts(
        "19.99", [{"kind": PCT, "value": "0"}, {"kind": AMT, "value": "0.00"}]
    ) == "19.99"


@pytest.mark.parametrize(
    "subtotal,expected",
    [
        ("7.5", "7.50"),
        ("12", "12.00"),
        ("100.00", "100.00"),
        ("0.005", "0.00"),  # half-even tie, preceding digit 0 is already even
        ("0.015", "0.02"),  # half-even tie, preceding digit 1 rounds up to 2
        ("-0.00", "0.00"),  # "zero is returned as 0.00, never -0.00"
    ],
)
def test_empty_stack_returns_the_normalised_subtotal(subtotal, expected):
    """Rule 5 plus SPEC "Money representation" on the sign of zero."""
    assert impl.apply_discounts(subtotal, []) == expected


def test_output_always_has_exactly_two_decimal_places():
    """SPEC "Money representation": "The returned string always carries exactly two"."""
    for result in (
        impl.apply_discounts("1234.567", []),
        impl.apply_discounts("0.00", [{"kind": PCT, "value": "33.33"}]),
        impl.apply_discounts("100", [{"kind": AMT, "value": "100"}]),
    ):
        assert isinstance(result, str)
        assert len(result.split(".")[1]) == 2


def test_input_is_not_mutated():
    """SPEC "What to build": "It must not mutate discounts or any mapping inside it"."""
    discounts = [{"kind": PCT, "value": "20"}, {"kind": AMT, "value": "5.00"}]
    impl.apply_discounts("100.00", discounts)
    assert discounts == [{"kind": PCT, "value": "20"}, {"kind": AMT, "value": "5.00"}]


@pytest.mark.parametrize("bad", ["", " 5.00", "+5.00", "5,000.00", "1e3", "abc", "5.", ".5", "NaN"])
def test_malformed_subtotal_raises_value_error(bad):
    """SPEC "Money representation" grammar plus the first bullet of "Errors"."""
    with pytest.raises(ValueError):
        impl.apply_discounts(bad, [])


def test_negative_subtotal_raises_value_error_naming_it():
    """SPEC "Errors": "subtotal is negative"; the message names the offender."""
    with pytest.raises(ValueError) as excinfo:
        impl.apply_discounts("-1.00", [])
    assert "-1.00" in str(excinfo.value)


@pytest.mark.parametrize("kind", [PCT, AMT])
def test_negative_discount_value_raises_value_error(kind):
    """SPEC "Errors": "value is negative, for either kind"."""
    with pytest.raises(ValueError) as excinfo:
        impl.apply_discounts("10.00", [{"kind": kind, "value": "-1.00"}])
    assert "-1.00" in str(excinfo.value)


@pytest.mark.parametrize("value", ["100.01", "101", "250"])
def test_percent_above_one_hundred_raises_value_error(value):
    """SPEC "Errors": "value is greater than 100 for a percent discount"."""
    with pytest.raises(ValueError) as excinfo:
        impl.apply_discounts("10.00", [{"kind": PCT, "value": value}])
    assert value in str(excinfo.value)


def test_large_amount_discount_is_allowed_not_an_error():
    """SPEC "Errors": "There is no upper bound on an amount discount"."""
    assert impl.apply_discounts("10.00", [{"kind": AMT, "value": "1000000.00"}]) == "0.00"


@pytest.mark.parametrize("kind", ["bogo", "PERCENT", "Percent", "", "shipping", None, 5])
def test_unknown_kind_raises_value_error(kind):
    """SPEC "Errors": kind is anything other than "percent" or "amount"."""
    with pytest.raises(ValueError):
        impl.apply_discounts("10.00", [{"kind": kind, "value": "10"}])


@pytest.mark.parametrize(
    "entry", [{"kind": PCT}, {"value": "10"}, {}, "20%", None, ["percent", "20"]]
)
def test_malformed_discount_entry_raises_value_error(entry):
    """SPEC "Errors": not a mapping, or missing "kind" or "value"."""
    with pytest.raises(ValueError):
        impl.apply_discounts("10.00", [entry])


def test_validation_is_unconditional_after_a_clamp():
    """SPEC "Errors": an invalid discount raises "even if the running total has
    already been clamped to 0.00"."""
    with pytest.raises(ValueError):
        impl.apply_discounts(
            "1.00", [{"kind": AMT, "value": "50.00"}, {"kind": PCT, "value": "150"}]
        )
