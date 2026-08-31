"""Authoritative examples for PLAT-2291.

Every assertion here is traceable to the cited source or to an explicit sentence
of SPEC.md, not to whatever the reference implementation happens to do.
``make verify-corpus`` runs this against ``reference.py`` in CI, which is what
lets the README claim that ground-truth labels are verified by construction
rather than by inspection.

Source: AWS Architecture Blog, "Exponential Backoff And Jitter",
https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
Full Jitter:  sleep = random_between(0, min(cap, base * 2 ** attempt))
"""

import math

import pytest

import impl

MAX = lambda upper: upper          # noqa: E731 - worst case draw
ZERO = lambda upper: 0.0           # noqa: E731 - best case draw
HALF = lambda upper: upper / 2     # noqa: E731 - midpoint draw


def test_ceiling_sequence_is_min_cap_base_times_two_to_the_attempt():
    """Full Jitter: the draw's upper bound is min(cap, base * 2**attempt)."""
    assert impl.schedule(6, 1.0, 10.0, MAX) == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0]


def test_attempt_zero_is_already_jittered():
    """SPEC: 'The first delay is rand(min(cap, base)), not base.'"""
    assert impl.schedule(1, 1.0, 10.0, ZERO) == [0.0]
    assert impl.schedule(1, 1.0, 10.0, MAX) == [1.0]


def test_there_is_no_additive_base_term():
    """SPEC: 'The delay is the draw and nothing but the draw' (Equal Jitter is
    the variant that adds a fixed component; we are not using it)."""
    assert impl.schedule(5, 2.0, 60.0, ZERO) == [0.0, 0.0, 0.0, 0.0, 0.0]


def test_cap_bounds_the_ceiling_not_the_drawn_delay():
    """SPEC: 'The cap is applied to base * 2**i before the draw.'

    With a midpoint draw the capped attempts must yield cap/2.  Clamping after
    the draw would give 8.0 and 10.0 for the last two entries instead.
    """
    assert impl.schedule(6, 1.0, 10.0, HALF) == [0.5, 1.0, 2.0, 4.0, 5.0, 5.0]


def test_worked_example_from_the_ticket():
    """SPEC worked example: base=0.2, cap=5.0, attempts=6."""
    assert impl.schedule(6, 0.2, 5.0, MAX) == [0.2, 0.4, 0.8, 1.6, 3.2, 5.0]
    assert impl.schedule(6, 0.2, 5.0, HALF) == [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]


def test_cap_below_base_flattens_every_ceiling_including_attempt_zero():
    """SPEC: 'cap < base is legitimate... Every ceiling is then cap, including
    the one for attempt 0.'"""
    assert impl.schedule(4, 10.0, 2.0, MAX) == [2.0, 2.0, 2.0, 2.0]


def test_cap_equal_to_base_behaves_the_same_way():
    """SPEC: 'cap == base behaves the same way.'"""
    assert impl.schedule(3, 3.0, 3.0, MAX) == [3.0, 3.0, 3.0]


def test_result_length_equals_attempts():
    """SPEC: 'Return a new list of attempts delays.'"""
    for n in (0, 1, 2, 7, 33):
        assert len(impl.schedule(n, 0.5, 4.0, MAX)) == n


def test_rand_is_called_once_per_attempt_in_order_with_the_ceiling():
    """SPEC: 'rand must be called exactly once per attempt, in attempt order,
    with ceiling_i as its single argument.'"""
    seen = []

    def recording(upper):
        seen.append(upper)
        return upper / 4

    result = impl.schedule(5, 1.0, 6.0, recording)
    assert seen == [1.0, 2.0, 4.0, 6.0, 6.0]
    assert result == [0.25, 0.5, 1.0, 1.5, 1.5]


def test_drawn_value_is_returned_unchanged():
    """SPEC: 'Return each drawn value unchanged: do not clamp it, round it,
    floor it at some minimum, or add anything to it.'"""
    assert impl.schedule(3, 1.0, 100.0, lambda upper: upper * 0.3) == [0.3, 0.6, 1.2]


def test_large_attempt_count_does_not_overflow():
    """SPEC: 'schedule(2000, 1.0, 30.0, rand) must return 2000 finite delays
    without raising.'"""
    result = impl.schedule(2000, 1.0, 30.0, MAX)
    assert len(result) == 2000
    assert result[:6] == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
    assert result[-1] == 30.0
    assert all(math.isfinite(x) and 0.0 <= x <= 30.0 for x in result)


def test_zero_attempts_returns_empty_list():
    """SPEC: 'attempts == 0 returns an empty list. It is not an error.'"""
    assert impl.schedule(0, 1.0, 10.0, MAX) == []


def test_negative_attempts_raises_value_error_naming_the_parameter():
    """SPEC: 'attempts < 0 raises ValueError' with the parameter named."""
    with pytest.raises(ValueError) as excinfo:
        impl.schedule(-1, 1.0, 10.0, MAX)
    assert "attempts" in str(excinfo.value)


@pytest.mark.parametrize("bad", [0.0, -0.0, -1.0, -1e-9, float("inf"), float("nan")])
def test_invalid_base_raises_value_error_naming_the_parameter(bad):
    """SPEC: 'base and cap must each be a finite number strictly greater than
    zero. Zero, negative, inf and nan all raise ValueError.'"""
    with pytest.raises(ValueError) as excinfo:
        impl.schedule(3, bad, 10.0, MAX)
    assert "base" in str(excinfo.value)


@pytest.mark.parametrize("bad", [0.0, -2.5, float("-inf"), float("nan")])
def test_invalid_cap_raises_value_error_naming_the_parameter(bad):
    """SPEC: same sentence, applied to cap."""
    with pytest.raises(ValueError) as excinfo:
        impl.schedule(3, 1.0, bad, MAX)
    assert "cap" in str(excinfo.value)


def test_validation_order_is_attempts_then_base_then_cap():
    """SPEC: 'Validate in the order attempts, then base, then cap.'"""
    with pytest.raises(ValueError) as excinfo:
        impl.schedule(-1, 0.0, 0.0, MAX)
    assert "attempts" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        impl.schedule(2, 0.0, 0.0, MAX)
    assert "base" in str(excinfo.value)


def test_returns_a_new_list_each_call():
    """SPEC: 'Return a new list.'"""
    first = impl.schedule(3, 1.0, 10.0, MAX)
    second = impl.schedule(3, 1.0, 10.0, MAX)
    assert first == second
    assert first is not second
