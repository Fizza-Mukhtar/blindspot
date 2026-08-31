import impl
import pytest
import math


def test_example_from_ticket():
    """Test the exact example from the ticket"""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
    assert result == expected


def test_empty_schedule():
    """attempts == 0 returns empty list"""
    result = impl.schedule(0, 0.1, 1.0, lambda u: u)
    assert result == []


def test_single_attempt():
    """Single attempt uses base as ceiling"""
    result = impl.schedule(1, 0.5, 10.0, lambda u: u)
    assert result == [0.5]


def test_best_case_zero_rand():
    """Rand returning 0 gives minimum delays"""
    result = impl.schedule(4, 1.0, 10.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0, 0.0]


def test_worst_case_max_rand():
    """Rand returning upper bound gives maximum delays"""
    result = impl.schedule(4, 1.0, 10.0, lambda u: u)
    # Ceilings: 1, 2, 4, 8
    assert result == [1.0, 2.0, 4.0, 8.0]


def test_cap_clamping_applied():
    """Cap prevents exponential growth"""
    result = impl.schedule(6, 1.0, 5.0, lambda u: u)
    # Ceilings: 1, 2, 4, 5 (capped from 8), 5, 5
    assert result == [1.0, 2.0, 4.0, 5.0, 5.0, 5.0]


def test_cap_equals_base_flat_schedule():
    """When cap == base, all ceilings are the same"""
    result = impl.schedule(5, 2.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0, 2.0, 2.0]


def test_large_attempts_no_overflow():
    """2000 attempts with exponential backoff should not overflow"""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: u / 2)
    assert len(result) == 2000
    # All delays should be finite and within [0, cap]
    for delay in result:
        assert math.isfinite(delay), f"Delay {delay} is not finite"
        assert 0.0 <= delay <= 30.0, f"Delay {delay} outside bounds [0, 30]"


def test_small_base_and_cap():
    """Very small values should work correctly"""
    result = impl.schedule(4, 0.001, 0.01, lambda u: u)
    # Ceilings: 0.001, 0.002, 0.004, 0.008
    assert result == [0.001, 0.002, 0.004, 0.008]


def test_large_base_and_cap():
    """Large values should work correctly"""
    result = impl.schedule(3, 1000.0, 10000.0, lambda u: u)
    assert result == [1000.0, 2000.0, 4000.0]


def test_attempts_negative_raises():
    """attempts < 0 raises ValueError with 'attempts' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(-1, 0.1, 1.0, lambda u: u)
    assert "attempts" in str(exc.value)


def test_base_zero_raises():
    """base == 0 raises ValueError with 'base' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, 0.0, 1.0, lambda u: u)
    assert "base" in str(exc.value)


def test_base_negative_raises():
    """base < 0 raises ValueError with 'base' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, -0.5, 1.0, lambda u: u)
    assert "base" in str(exc.value)


def test_base_infinite_raises():
    """base == inf raises ValueError with 'base' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, float('inf'), 1.0, lambda u: u)
    assert "base" in str(exc.value)


def test_base_nan_raises():
    """base == nan raises ValueError with 'base' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, float('nan'), 1.0, lambda u: u)
    assert "base" in str(exc.value)


def test_cap_zero_raises():
    """cap == 0 raises ValueError with 'cap' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, 0.1, 0.0, lambda u: u)
    assert "cap" in str(exc.value)


def test_cap_negative_raises():
    """cap < 0 raises ValueError with 'cap' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, 0.1, -1.0, lambda u: u)
    assert "cap" in str(exc.value)


def test_cap_infinite_raises():
    """cap == inf raises ValueError with 'cap' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, 0.1, float('inf'), lambda u: u)
    assert "cap" in str(exc.value)


def test_cap_nan_raises():
    """cap == nan raises ValueError with 'cap' in message"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, 0.1, float('nan'), lambda u: u)
    assert "cap" in str(exc.value)


def test_validation_order_attempts_then_base():
    """Validation checks attempts before base"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(-1, 0.0, 1.0, lambda u: u)
    assert "attempts" in str(exc.value), "Should report attempts error first"


def test_validation_order_base_then_cap():
    """Validation checks base before cap"""
    with pytest.raises(ValueError) as exc:
        impl.schedule(1, 0.0, 0.0, lambda u: u)
    assert "base" in str(exc.value), "Should report base error before cap error"


def test_rand_receives_correct_ceilings():
    """Verify rand is called with correct ceiling values"""
    calls = []
    
    def tracking_rand(upper):
        calls.append(upper)
        return upper / 2
    
    result = impl.schedule(4, 1.0, 10.0, tracking_rand)
    # Expected ceilings: 1.0, 2.0, 4.0, 8.0
    assert calls == [1.0, 2.0, 4.0, 8.0]
    assert result == [0.5, 1.0, 2.0, 4.0]


def test_rand_result_used_unchanged():
    """Verify rand result is returned as-is without modification"""
    def custom_rand(upper):
        return upper * 0.75
    
    result = impl.schedule(3, 2.0, 100.0, custom_rand)
    # Ceilings: 2.0, 4.0, 8.0
    # Results: 1.5, 3.0, 6.0
    assert result == [1.5, 3.0, 6.0]
