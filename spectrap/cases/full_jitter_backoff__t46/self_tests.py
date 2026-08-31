import pytest
import math
import impl


def test_example_from_ticket():
    """Verify the exact example from the ticket."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
    assert result == expected


def test_empty_attempts():
    """attempts == 0 should return empty list."""
    result = impl.schedule(0, 1.0, 10.0, lambda u: u)
    assert result == []


def test_single_attempt():
    """Single attempt should return list with one element."""
    result = impl.schedule(1, 1.0, 10.0, lambda u: u)
    assert len(result) == 1
    assert result[0] == 1.0


def test_large_attempts_no_overflow():
    """Large attempts should not overflow or raise."""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: u)
    assert len(result) == 2000
    assert all(math.isfinite(d) for d in result)
    assert all(d <= 30.0 for d in result)


def test_zero_and_max_rand():
    """Verify rand behavior with zero and maximum returns."""
    # With lambda u: 0.0, all delays are 0
    result = impl.schedule(3, 1.0, 10.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0]
    
    # With lambda u: u, verify ceilings
    result = impl.schedule(5, 1.0, 10.0, lambda u: u)
    assert result == [1.0, 2.0, 4.0, 8.0, 10.0]


def test_cap_below_and_equals_base():
    """Cap at or below base gives flat ceiling."""
    # Cap below base
    result = impl.schedule(3, 10.0, 5.0, lambda u: u / 2)
    assert result == [2.5, 2.5, 2.5]
    
    # Cap equals base
    result = impl.schedule(3, 10.0, 10.0, lambda u: u)
    assert result == [10.0, 10.0, 10.0]


def test_small_and_large_values():
    """Verify extreme but valid base and cap values."""
    # Very small
    result = impl.schedule(3, 0.001, 0.01, lambda u: u)
    assert result == [0.001, 0.002, 0.004]
    
    # Large
    result = impl.schedule(3, 1000.0, 10000.0, lambda u: u)
    assert result == [1000.0, 2000.0, 4000.0]


def test_negative_attempts_raises():
    """attempts < 0 should raise ValueError."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 1.0, 10.0, lambda u: u)


def test_base_invalid_raises():
    """base must be finite and > 0."""
    # base == 0
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, 0.0, 10.0, lambda u: u)
    
    # base < 0
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, -1.0, 10.0, lambda u: u)
    
    # base == inf
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, float('inf'), 10.0, lambda u: u)
    
    # base == nan (critical: nan <= 0 is False, so must check isfinite)
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, float('nan'), 10.0, lambda u: u)


def test_cap_invalid_raises():
    """cap must be finite and > 0."""
    # cap == 0
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, 0.0, lambda u: u)
    
    # cap < 0
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, -10.0, lambda u: u)
    
    # cap == inf
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, float('inf'), lambda u: u)
    
    # cap == nan
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, float('nan'), lambda u: u)


def test_validation_order():
    """Validation should be: attempts, base, cap."""
    # attempts checked before base
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 0.0, 10.0, lambda u: u)
    
    # base checked before cap
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, 0.0, 0.0, lambda u: u)


def test_rand_called_with_correct_ceilings():
    """rand should be called once per attempt with correct ceilings."""
    ceilings = []
    
    def tracking_rand(upper):
        assert upper > 0, f"Expected positive ceiling, got {upper}"
        ceilings.append(upper)
        return 0.0
    
    impl.schedule(5, 2.0, 20.0, tracking_rand)
    expected = [2.0, 4.0, 8.0, 16.0, 20.0]
    assert ceilings == expected


def test_rand_return_value_used_directly():
    """Delay should be exactly what rand returns, unchanged."""
    result = impl.schedule(3, 0.5, 5.0, lambda u: u * 0.7)
    expected = [0.35, 0.7, 1.4]
    assert result == expected


def test_result_properties():
    """Result should have correct structure and constraints."""
    result = impl.schedule(10, 1.0, 5.0, lambda u: u)
    
    # Should be a list
    assert isinstance(result, list)
    
    # Length should equal attempts
    assert len(result) == 10
    
    # All delays should be finite
    assert all(math.isfinite(d) for d in result)
    
    # All delays should be <= cap
    assert all(d <= 5.0 for d in result)
