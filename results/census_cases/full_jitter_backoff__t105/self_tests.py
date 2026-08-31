import impl
import pytest
import math


def test_empty_schedule():
    """attempts == 0 returns empty list"""
    result = impl.schedule(0, 1.0, 5.0, lambda u: u)
    assert result == []


def test_single_attempt():
    """Single attempt returns list with one delay"""
    result = impl.schedule(1, 0.2, 5.0, lambda u: u / 2)
    assert result == [0.1]


def test_multiple_attempts_identity_rand():
    """Multiple attempts with identity rand function"""
    result = impl.schedule(3, 0.2, 5.0, lambda u: u)
    assert result == [0.2, 0.4, 0.8]


def test_multiple_attempts_zero_rand():
    """Multiple attempts with zero-returning rand"""
    result = impl.schedule(3, 0.2, 5.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0]


def test_cap_limits_ceiling():
    """Cap properly limits the ceiling"""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    assert len(result) == 6
    assert result[5] == 2.5  # Last ceiling capped at 5.0


def test_cap_equals_base():
    """Cap equal to base gives flat jittered delays"""
    result = impl.schedule(4, 1.0, 1.0, lambda u: u)
    assert result == [1.0, 1.0, 1.0, 1.0]


def test_cap_below_base():
    """Cap below base is legitimate"""
    result = impl.schedule(3, 5.0, 1.0, lambda u: u)
    assert result == [1.0, 1.0, 1.0]


def test_large_attempts_with_cap():
    """Large attempt count doesn't overflow"""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: 1.0)
    assert len(result) == 2000
    assert all(math.isfinite(d) for d in result)
    assert all(0 <= d <= 30.0 for d in result)


def test_exponential_growth_within_cap():
    """Exponential growth up to cap"""
    result = impl.schedule(5, 1.0, 100.0, lambda u: u)
    assert result == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_attempts_negative():
    """attempts < 0 raises ValueError with parameter name"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(-1, 1.0, 5.0, lambda u: u)
    assert str(exc_info.value) == "attempts"


def test_base_zero():
    """base == 0 raises ValueError"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 0.0, 5.0, lambda u: u)
    assert str(exc_info.value) == "base"


def test_base_negative():
    """base < 0 raises ValueError"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, -1.0, 5.0, lambda u: u)
    assert str(exc_info.value) == "base"


def test_base_inf():
    """base == inf raises ValueError"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, float('inf'), 5.0, lambda u: u)
    assert str(exc_info.value) == "base"


def test_base_nan():
    """base == nan raises ValueError"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, float('nan'), 5.0, lambda u: u)
    assert str(exc_info.value) == "base"


def test_cap_zero():
    """cap == 0 raises ValueError"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 1.0, 0.0, lambda u: u)
    assert str(exc_info.value) == "cap"


def test_cap_negative():
    """cap < 0 raises ValueError"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 1.0, -5.0, lambda u: u)
    assert str(exc_info.value) == "cap"


def test_cap_inf():
    """cap == inf raises ValueError"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 1.0, float('inf'), lambda u: u)
    assert str(exc_info.value) == "cap"


def test_cap_nan():
    """cap == nan raises ValueError"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 1.0, float('nan'), lambda u: u)
    assert str(exc_info.value) == "cap"


def test_validation_order_attempts_first():
    """Validation checks attempts before base and cap"""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(-1, 0.0, 0.0, lambda u: u)
    assert str(exc_info.value) == "attempts"
