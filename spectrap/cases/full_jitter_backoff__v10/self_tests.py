import pytest
import impl
import math


def test_worked_example_identity():
    """schedule(6, 0.2, 5.0, lambda u: u) == [0.2, 0.4, 0.8, 1.6, 3.2, 5.0]"""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u)
    assert result == [0.2, 0.4, 0.8, 1.6, 3.2, 5.0]


def test_worked_example_zeros():
    """schedule(6, 0.2, 5.0, lambda u: 0.0) == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]"""
    result = impl.schedule(6, 0.2, 5.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_worked_example_half():
    """schedule(6, 0.2, 5.0, lambda u: u / 2) == [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]"""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    assert result == [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]


def test_zero_attempts_returns_empty_list():
    """attempts=0 returns empty list, not an error."""
    result = impl.schedule(0, 1.0, 10.0, lambda u: u)
    assert result == []


def test_single_attempt():
    """Single attempt returns single-element list with base as ceiling."""
    result = impl.schedule(1, 1.0, 10.0, lambda u: u)
    assert result == [1.0]


def test_exponential_growth():
    """Without capping, delays double each iteration: base, base*2, base*4, ..."""
    result = impl.schedule(4, 1.0, 100.0, lambda u: u)
    assert result == [1.0, 2.0, 4.0, 8.0]


def test_cap_less_than_base():
    """cap < base is legitimate; all ceilings are cap."""
    result = impl.schedule(3, 10.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0]


def test_cap_equals_base():
    """cap == base; all ceilings are cap (which equals base)."""
    result = impl.schedule(3, 5.0, 5.0, lambda u: u)
    assert result == [5.0, 5.0, 5.0]


def test_cap_applies_at_correct_point():
    """Cap is applied once base * 2**i >= cap."""
    result = impl.schedule(5, 1.0, 4.0, lambda u: u)
    assert result == [1.0, 2.0, 4.0, 4.0, 4.0]


def test_negative_attempts_raises_valueerror():
    """attempts < 0 raises ValueError with 'attempts' in message."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 1.0, 10.0, lambda u: u)


def test_invalid_base_raises_valueerror():
    """base that is 0, negative, inf, or nan raises ValueError('base')."""
    for bad_base in [0.0, -1.0, float('inf'), float('nan')]:
        with pytest.raises(ValueError, match="base"):
            impl.schedule(5, bad_base, 10.0, lambda u: u)


def test_invalid_cap_raises_valueerror():
    """cap that is 0, negative, inf, or nan raises ValueError('cap')."""
    for bad_cap in [0.0, -1.0, float('inf'), float('nan')]:
        with pytest.raises(ValueError, match="cap"):
            impl.schedule(5, 1.0, bad_cap, lambda u: u)


def test_validation_order_attempts_before_base():
    """Validation checks attempts before base."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 0.0, 10.0, lambda u: u)


def test_validation_order_base_before_cap():
    """Validation checks base before cap."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, 0.0, -1.0, lambda u: u)


def test_rand_called_once_per_attempt_with_correct_ceilings():
    """rand is called exactly once per attempt with correct ceiling values in order."""
    calls = []

    def recording_rand(upper):
        calls.append(upper)
        return 0.0

    impl.schedule(6, 0.2, 5.0, recording_rand)
    assert calls == [0.2, 0.4, 0.8, 1.6, 3.2, 5.0]


def test_returned_delays_unchanged_from_rand():
    """Returned delays are exactly what rand returns, without modification."""
    test_values = [0.1, 0.5, 1.5, 2.7, 3.14]
    call_count = [0]

    def returning_rand(upper):
        value = test_values[call_count[0]]
        call_count[0] += 1
        return value

    result = impl.schedule(5, 1.0, 100.0, returning_rand)
    assert result == test_values


def test_large_attempt_count_no_overflow():
    """schedule(2000, ...) computes without overflow and returns finite delays in [0, cap]."""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: 1.0)
    assert len(result) == 2000
    assert all(math.isfinite(d) for d in result)
    assert all(0 <= d <= 30.0 for d in result)
