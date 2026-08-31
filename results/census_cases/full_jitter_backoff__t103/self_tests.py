import impl
import pytest

def test_schedule_example_from_ticket():
    """Test the example from the ticket: base=0.2, cap=5.0, attempts=6, rand=lambda u: u/2"""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
    assert result == expected

def test_schedule_zero_attempts():
    """Test with attempts=0, should return empty list"""
    result = impl.schedule(0, 1.0, 10.0, lambda u: u)
    assert result == []

def test_schedule_single_attempt():
    """Test with attempts=1"""
    result = impl.schedule(1, 1.0, 10.0, lambda u: u)
    assert result == [1.0]

def test_schedule_worst_case_rand():
    """Test with rand=lambda u: u (worst case, always returns upper bound)"""
    result = impl.schedule(3, 1.0, 10.0, lambda u: u)
    expected = [1.0, 2.0, 4.0]
    assert result == expected

def test_schedule_best_case_rand():
    """Test with rand=lambda u: 0.0 (best case, always returns 0)"""
    result = impl.schedule(3, 1.0, 10.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0]

def test_schedule_cap_hit_and_clamped():
    """Test that delays are clamped at cap"""
    result = impl.schedule(5, 1.0, 4.0, lambda u: u)
    assert result == [1.0, 2.0, 4.0, 4.0, 4.0]

def test_schedule_cap_lower_than_base():
    """Test with cap lower than base (flat fully jittered delay)"""
    result = impl.schedule(3, 5.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0]

def test_schedule_large_attempts_no_overflow():
    """Test with large number of attempts (should not overflow)"""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: 0)
    assert len(result) == 2000
    assert all(d == 0.0 for d in result)

def test_schedule_negative_attempts_raises():
    """Test that negative attempts raises ValueError"""
    with pytest.raises(ValueError, match="attempts: must be >= 0"):
        impl.schedule(-1, 1.0, 10.0, lambda u: u)

def test_schedule_invalid_base_raises():
    """Test that invalid base values raise ValueError"""
    with pytest.raises(ValueError, match="base: must be finite and > 0"):
        impl.schedule(1, 0.0, 10.0, lambda u: u)
    
    with pytest.raises(ValueError, match="base: must be finite and > 0"):
        impl.schedule(1, -1.0, 10.0, lambda u: u)
    
    with pytest.raises(ValueError, match="base: must be finite and > 0"):
        impl.schedule(1, float('inf'), 10.0, lambda u: u)
    
    with pytest.raises(ValueError, match="base: must be finite and > 0"):
        impl.schedule(1, float('nan'), 10.0, lambda u: u)

def test_schedule_invalid_cap_raises():
    """Test that invalid cap values raise ValueError"""
    with pytest.raises(ValueError, match="cap: must be finite and > 0"):
        impl.schedule(1, 1.0, 0.0, lambda u: u)
    
    with pytest.raises(ValueError, match="cap: must be finite and > 0"):
        impl.schedule(1, 1.0, -1.0, lambda u: u)
    
    with pytest.raises(ValueError, match="cap: must be finite and > 0"):
        impl.schedule(1, 1.0, float('inf'), lambda u: u)
    
    with pytest.raises(ValueError, match="cap: must be finite and > 0"):
        impl.schedule(1, 1.0, float('nan'), lambda u: u)

def test_schedule_validation_order():
    """Test that validation happens in order: attempts, base, cap"""
    # Multiple errors: attempts checked first
    with pytest.raises(ValueError, match="attempts: must be >= 0"):
        impl.schedule(-1, -1.0, -1.0, lambda u: u)
    
    # attempts OK, base and cap bad: base checked first
    with pytest.raises(ValueError, match="base: must be finite and > 0"):
        impl.schedule(1, -1.0, -1.0, lambda u: u)
    
    # attempts and base OK, cap bad
    with pytest.raises(ValueError, match="cap: must be finite and > 0"):
        impl.schedule(1, 1.0, -1.0, lambda u: u)

def test_schedule_rand_called_exact_times():
    """Test that rand is called exactly 'attempts' times"""
    call_count = [0]
    def counting_rand(upper):
        call_count[0] += 1
        return upper
    
    impl.schedule(5, 1.0, 100.0, counting_rand)
    assert call_count[0] == 5

def test_schedule_rand_called_with_correct_ceilings():
    """Test that rand is called with correct ceiling values"""
    call_args = []
    def recording_rand(upper):
        call_args.append(upper)
        return upper / 2
    
    impl.schedule(4, 1.0, 10.0, recording_rand)
    # Ceilings for base=1.0, cap=10.0: 1.0, 2.0, 4.0, 8.0
    assert call_args == [1.0, 2.0, 4.0, 8.0]

def test_schedule_rand_return_values_used_unchanged():
    """Test that rand return values are used as-is without modification"""
    result = impl.schedule(3, 1.0, 10.0, lambda u: u * 0.75)
    # Ceilings: 1.0, 2.0, 4.0
    # Expected: 0.75, 1.5, 3.0
    assert result == [0.75, 1.5, 3.0]

def test_schedule_very_small_base_and_cap():
    """Test with very small base and cap values"""
    result = impl.schedule(3, 0.001, 0.01, lambda u: u)
    expected = [0.001, 0.002, 0.004]
    assert result == expected

def test_schedule_cap_equals_base():
    """Test with cap equal to base"""
    result = impl.schedule(3, 1.0, 1.0, lambda u: u)
    assert result == [1.0, 1.0, 1.0]
