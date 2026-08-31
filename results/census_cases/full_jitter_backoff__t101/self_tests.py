import impl
import pytest
import math


def test_empty_attempts():
    """attempts=0 returns empty list."""
    result = impl.schedule(0, 1.0, 5.0, lambda u: u)
    assert result == []


def test_basic_example_from_ticket():
    """Test the example from the ticket: base=0.2, cap=5.0, attempts=6, rand=lambda u: u/2."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
    assert len(result) == 6
    for i, (r, e) in enumerate(zip(result, expected)):
        assert abs(r - e) < 1e-9


def test_worst_case_rand():
    """Worst case: rand returns ceiling value."""
    result = impl.schedule(3, 0.5, 4.0, lambda u: u)
    assert result == [0.5, 1.0, 2.0]


def test_best_case_rand():
    """Best case: rand returns 0."""
    result = impl.schedule(5, 1.0, 8.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0, 0.0, 0.0]


def test_cap_equals_base():
    """cap equals base results in constant ceiling."""
    result = impl.schedule(4, 2.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0, 2.0]


def test_cap_less_than_base():
    """cap < base is legitimate."""
    result = impl.schedule(3, 5.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0]


def test_ceilings_progression_until_capped():
    """Ceilings double until cap is reached, then stay constant."""
    result = impl.schedule(7, 1.0, 16.0, lambda u: u)
    expected = [1.0, 2.0, 4.0, 8.0, 16.0, 16.0, 16.0]
    assert result == expected


def test_large_attempts_no_overflow():
    """2000 attempts works without overflow."""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: u)
    assert len(result) == 2000
    for delay in result:
        assert math.isfinite(delay)
        assert 0 <= delay <= 30.0


def test_attempts_negative_raises():
    """attempts < 0 raises ValueError."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 1.0, 5.0, lambda u: u)


def test_base_zero_raises():
    """base = 0 raises ValueError."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, 0.0, 5.0, lambda u: u)


def test_base_negative_raises():
    """base < 0 raises ValueError."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, -1.0, 5.0, lambda u: u)


def test_base_inf_raises():
    """base = inf raises ValueError."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, float('inf'), 5.0, lambda u: u)


def test_base_nan_raises():
    """base = nan raises ValueError (explicit finiteness check)."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, float('nan'), 5.0, lambda u: u)


def test_cap_zero_raises():
    """cap = 0 raises ValueError."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, 0.0, lambda u: u)


def test_cap_negative_raises():
    """cap < 0 raises ValueError."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, -5.0, lambda u: u)


def test_cap_inf_raises():
    """cap = inf raises ValueError."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, float('inf'), lambda u: u)


def test_cap_nan_raises():
    """cap = nan raises ValueError (explicit finiteness check)."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, float('nan'), lambda u: u)


def test_validation_order_attempts_first():
    """Validation checks attempts before base and cap."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 0.0, 0.0, lambda u: u)


def test_validation_order_base_before_cap():
    """Validation checks base before cap."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, 0.0, 0.0, lambda u: u)
