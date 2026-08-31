"""Authoritative examples for RATE-338.

Every assertion here is taken either from the cited standard or from an explicit
sentence of SPEC.md, not from the reference implementation's behaviour.
``make verify-corpus`` runs this against ``reference.py`` in CI, which is what
lets the README claim that ground-truth labels are verified by construction
rather than by inspection.

Source: RFC 2697 section 2, the committed bucket of the single rate three color
marker -- https://datatracker.ietf.org/doc/html/rfc2697
"""

import math

import pytest

import impl


def test_bucket_starts_full():
    """RFC 2697 s2: the token count is initially full, Tc(0) = CBS.

    Restated in SPEC.md: "The bucket starts full: before the first entry the
    token count is `capacity`."
    """
    assert impl.simulate(5.0, 1.0, [(0.0, 5.0)]) == [True]


def test_worked_example_from_the_ticket():
    """SPEC.md worked example: capacity 10, rate 1, four entries."""
    trace = [(0.0, 10.0), (5.0, 10.0), (6.0, 10.0), (10.0, 10.0)]
    assert impl.simulate(10.0, 1.0, trace) == [True, False, False, True]


def test_accrual_mark_advances_across_a_rejection():
    """SPEC.md step 2 (INC-2251): the mark advances for every entry.

    Entry 2 accrues from t=5, the rejected entry's timestamp, so it gains one
    token and stays rejected. Counting the interval from t=0 a second time
    would fill the bucket and admit it.
    """
    trace = [(0.0, 10.0), (5.0, 10.0), (6.0, 10.0)]
    assert impl.simulate(10.0, 1.0, trace) == [True, False, False]


def test_continuous_accrual_at_sub_second_polls():
    """SPEC.md step 1 (INC-2214): accrual is elapsed * rate, never floored.

    Ten polls a second at 1 token/second accrue 0.1 tokens each; flooring to
    whole tokens would report every one of them as rejected.
    """
    trace = [(0.0, 1.0), (0.1, 0.1), (0.2, 0.1), (0.3, 0.1), (0.4, 0.1), (0.5, 0.1)]
    assert impl.simulate(1.0, 1.0, trace) == [True, True, True, True, True, True]


def test_fractional_accrual_over_a_fractional_rate():
    """SPEC.md: "A gap of 40 milliseconds at 5 tokens/second accrues 0.2 tokens."""
    trace = [(0.0, 1.0), (0.04, 0.2), (0.08, 0.2), (0.08, 0.2)]
    assert impl.simulate(1.0, 5.0, trace) == [True, True, True, False]


def test_token_count_is_clamped_at_capacity():
    """RFC 2697 s2: Tc is incremented only "if Tc < CBS" -- never past the bucket.

    A 100-second idle at 10 tokens/second would accrue 1000 tokens unclamped;
    the bucket holds 5, so the third entry finds an empty bucket.
    """
    trace = [(0.0, 5.0), (100.0, 5.0), (100.0, 1.0)]
    assert impl.simulate(5.0, 10.0, trace) == [True, True, False]


def test_cost_exceeding_capacity_is_never_admitted_and_consumes_nothing():
    """SPEC.md: a cost above `capacity + 1e-9` can never be admitted, and by
    step 4 consumes nothing, so the next entry still sees the full bucket."""
    assert impl.simulate(5.0, 1.0, [(0.0, 6.0), (0.0, 5.0)]) == [False, True]


def test_rejection_leaves_the_token_count_untouched():
    """RFC 2697 s2: a non-green packet leaves Tc unchanged.

    After spending 4 of 5 tokens, a 2-token request is rejected; the 1-token
    request behind it still finds the remaining token.
    """
    assert impl.simulate(5.0, 1.0, [(0.0, 4.0), (0.0, 2.0), (0.0, 1.0)]) == [
        True,
        False,
        True,
    ]


def test_cost_equal_to_the_credit_on_hand_is_admitted():
    """RFC 2697 s2: green when Tc - B >= 0, i.e. equality is admitted.

    SPEC.md step 3: "a request costing exactly the credit on hand is admitted."
    """
    assert impl.simulate(2.0, 1.0, [(0.0, 2.0), (1.0, 1.0), (1.5, 0.5)]) == [
        True,
        True,
        True,
    ]


def test_cost_above_the_credit_on_hand_is_rejected():
    """RFC 2697 s2: Tc - B < 0 is not green."""
    assert impl.simulate(2.0, 1.0, [(0.0, 2.0), (1.0, 1.5)]) == [True, False]


def test_admission_tolerance_is_one_nanotoken():
    """SPEC.md step 3: admitted when `tokens + 1e-9 >= cost`.

    Half a nanotoken over the credit on hand falls inside the slack; a
    microtoken over does not.
    """
    assert impl.simulate(2.0, 1.0, [(0.0, 2.0), (1.0, 1.0 + 5e-10)]) == [True, True]
    assert impl.simulate(2.0, 1.0, [(0.0, 2.0), (1.0, 1.0 + 1e-6)]) == [True, False]


def test_burst_at_a_shared_timestamp_accrues_nothing():
    """SPEC.md: "a burst recorded at the same instant accrues nothing between
    its members." Equal timestamps are legal (non-decreasing)."""
    trace = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]
    assert impl.simulate(3.0, 1.0, trace) == [True, True, True, False]


def test_zero_cost_is_admitted_against_an_empty_bucket():
    """SPEC.md: "A cost of exactly zero is legal and is always admitted, even
    against an empty bucket."""
    assert impl.simulate(1.0, 1.0, [(0.0, 1.0), (0.0, 0.0)]) == [True, True]


def test_empty_trace_returns_empty_list():
    """SPEC.md: "An empty trace returns an empty list."""
    assert impl.simulate(1.0, 1.0, []) == []


def test_decreasing_timestamp_raises():
    """SPEC.md: "If a timestamp is strictly less than the one before it, the
    trace is corrupt: raise ValueError."""
    with pytest.raises(ValueError):
        impl.simulate(1.0, 1.0, [(1.0, 0.5), (0.5, 0.5)])


@pytest.mark.parametrize(
    "capacity,rate",
    [
        (0.0, 1.0),
        (-1.0, 1.0),
        (float("inf"), 1.0),
        (float("nan"), 1.0),
        (1.0, 0.0),
        (1.0, -2.5),
        (1.0, float("inf")),
    ],
)
def test_non_positive_or_non_finite_parameters_raise(capacity, rate):
    """SPEC.md errors: capacity and refill_per_second must each be a finite
    number greater than zero."""
    with pytest.raises(ValueError):
        impl.simulate(capacity, rate, [(0.0, 0.5)])


@pytest.mark.parametrize("cost", [-1e-9, -0.5, -3.0, float("nan"), float("inf")])
def test_negative_or_non_finite_cost_raises(cost):
    """SPEC.md errors: a cost that is negative, or is not a finite number."""
    with pytest.raises(ValueError):
        impl.simulate(1.0, 1.0, [(0.0, cost)])


def test_non_finite_timestamp_raises():
    """SPEC.md errors: a timestamp that is not a finite number."""
    with pytest.raises(ValueError):
        impl.simulate(1.0, 1.0, [(0.0, 0.5), (math.inf, 0.5)])


def test_input_trace_is_not_mutated():
    """SPEC.md: "Do not mutate the input."""
    trace = [(0.0, 1.0), (1.0, 1.0)]
    copy = list(trace)
    impl.simulate(2.0, 1.0, trace)
    assert trace == copy
