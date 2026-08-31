import pytest
import impl
import math


def test_empty_schedule():
    """attempts == 0 returns an empty list."""
    result = impl.schedule(0, 1.0, 5.0, lambda u: u)
    assert result == []


def test_single_attempt():
    """Single attempt returns list with one element."""
    result = impl.schedule(1, 0.2, 5.0, lambda u: u)
    assert result == [0.2]


def test_worked_example_worst_case():
    """Worked example with worst-case rand (lambda u: u)."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u)
    assert result == [0.2, 0.4, 0.8, 1.6, 3.2, 5.0]


def test_worked_example_best_case():
    """Worked example with best-case rand (lambda u: 0.0)."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_worked_example_partial_jitter():
    """Worked example with partial jitter (lambda u: u / 2)."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    assert result == [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]


def test_cap_less_than_base():
    """cap < base results in flat schedule at cap."""
    result = impl.schedule(3, 1.0, 0.5, lambda u: u)
    assert result == [0.5, 0.5, 0.5]


def test_cap_equals_base():
    """cap == base results in flat schedule."""
    result = impl.schedule(3, 1.0, 1.0, lambda u: u)
    assert result == [1.0, 1.0, 1.0]


def test_large_attempt_count():
    """Large attempt count (2000) does not overflow."""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: u)
    assert len(result) == 2000
    for delay in result:
        assert math.isfinite(delay)
        assert 0 <= delay <= 30.0


def test_rand_called_once_per_attempt_with_correct_ceilings():
    """rand is called exactly once per attempt with correct ceiling values."""
    calls = []
    
    def tracking_rand(upper):
        calls.append(upper)
        return upper
    
    result = impl.schedule(4, 1.0, 10.0, tracking_rand)
    
    assert calls == [1.0, 2.0, 4.0, 8.0]
    assert result == [1.0, 2.0, 4.0, 8.0]


def test_delays_returned_unchanged_from_rand():
    """Returned delays are exactly what rand returns (no modification)."""
    def custom_rand(upper):
        return upper * 0.123
    
    result = impl.schedule(3, 1.0, 10.0, custom_rand)
    
    expected = [0.123, 0.246, 0.492]
    assert result == expected


def test_negative_attempts_raises_valueerror():
    """attempts < 0 raises ValueError with 'attempts' message."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 1.0, 5.0, lambda u: u)


def test_invalid_base_raises_valueerror():
    """Invalid base (zero, negative, inf, nan) raises ValueError."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, 0.0, 5.0, lambda u: u)
    
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, -1.0, 5.0, lambda u: u)
    
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, math.inf, 5.0, lambda u: u)
    
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, math.nan, 5.0, lambda u: u)


def test_invalid_cap_raises_valueerror():
    """Invalid cap (zero, negative, inf, nan) raises ValueError."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, 0.0, lambda u: u)
    
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, -5.0, lambda u: u)
    
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, math.inf, lambda u: u)
    
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, math.nan, lambda u: u)


def test_validation_order_attempts_before_others():
    """Validation checks attempts before base and cap."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 0.0, 0.0, lambda u: u)


def test_validation_order_base_before_cap():
    """Validation checks base before cap."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, 0.0, 0.0, lambda u: u)


def test_cap_stops_exponential_growth():
    """Once cap is reached, all subsequent ceilings are cap."""
    calls = []
    
    def tracking_rand(upper):
        calls.append(upper)
        return 0.0
    
    impl.schedule(6, 2.0, 10.0, tracking_rand)
    
    assert calls == [2.0, 4.0, 8.0, 10.0, 10.0, 10.0]
