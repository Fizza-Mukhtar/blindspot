import pytest
import impl
import math

def test_zero_attempts_returns_empty_list():
    """attempts == 0 gives an empty list and is not an error"""
    result = impl.schedule(0, 1.0, 5.0, lambda u: u)
    assert result == []

def test_single_attempt_with_identity_rand():
    """Single attempt with rand returning the ceiling"""
    result = impl.schedule(1, 0.2, 5.0, lambda u: u)
    assert result == [0.2]

def test_single_attempt_with_zero_rand():
    """Single attempt with rand returning 0"""
    result = impl.schedule(1, 0.2, 5.0, lambda u: 0.0)
    assert result == [0.0]

def test_multiple_attempts_with_identity_rand():
    """Multiple attempts with rand returning ceiling"""
    result = impl.schedule(3, 0.2, 5.0, lambda u: u)
    assert result == [0.2, 0.4, 0.8]

def test_multiple_attempts_with_zero_rand():
    """Multiple attempts with rand returning 0"""
    result = impl.schedule(3, 0.2, 5.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0]

def test_ticket_example():
    """Test the exact example from the ticket"""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
    assert result == expected

def test_ceilings_capped_correctly():
    """Verify that delays are capped correctly"""
    result = impl.schedule(5, 0.5, 1.0, lambda u: u)
    expected = [0.5, 1.0, 1.0, 1.0, 1.0]
    assert result == expected

def test_cap_below_base():
    """cap < base is legitimate, all ceilings are then cap"""
    result = impl.schedule(3, 5.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0]

def test_cap_equals_base():
    """cap == base is legitimate"""
    result = impl.schedule(3, 5.0, 5.0, lambda u: u)
    assert result == [5.0, 5.0, 5.0]

def test_large_attempts_without_overflow():
    """Test that 2000 attempts with cap works without overflow"""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: 0.0)
    assert len(result) == 2000
    assert all(x == 0.0 for x in result)

def test_large_attempts_respects_cap():
    """Test that all delays are within cap"""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: u)
    assert len(result) == 2000
    assert all(x <= 30.0 for x in result)
    assert result[-1] == 30.0

def test_negative_attempts_raises():
    """attempts < 0 raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 1.0, 5.0, lambda u: u)

def test_base_zero_raises():
    """base == 0 raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, 0, 5.0, lambda u: u)

def test_base_negative_raises():
    """base < 0 raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, -1.0, 5.0, lambda u: u)

def test_base_inf_raises():
    """base == inf raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, math.inf, 5.0, lambda u: u)

def test_base_nan_raises():
    """base == nan raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, math.nan, 5.0, lambda u: u)

def test_cap_zero_raises():
    """cap == 0 raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(5, 1.0, 0, lambda u: u)

def test_cap_negative_raises():
    """cap < 0 raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(5, 1.0, -5.0, lambda u: u)

def test_cap_inf_raises():
    """cap == inf raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(5, 1.0, math.inf, lambda u: u)

def test_cap_nan_raises():
    """cap == nan raises ValueError with parameter name"""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(5, 1.0, math.nan, lambda u: u)
