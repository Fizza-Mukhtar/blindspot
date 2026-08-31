import pytest
import math
import impl


def test_empty_schedule():
    """attempts == 0 returns an empty list."""
    result = impl.schedule(0, 0.2, 5.0, lambda u: u)
    assert result == []


def test_single_attempt():
    """Single attempt with worst case (rand returns upper)."""
    result = impl.schedule(1, 0.2, 5.0, lambda u: u)
    assert result == [0.2]


def test_worked_example_worst_case():
    """Worked example from ticket with lambda u: u."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u)
    assert result == [0.2, 0.4, 0.8, 1.6, 3.2, 5.0]


def test_worked_example_best_case():
    """Worked example from ticket with lambda u: 0.0."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_worked_example_mid_case():
    """Worked example from ticket with lambda u: u / 2."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
    assert result == expected


def test_large_attempt_count():
    """Large attempt count should not overflow or raise."""
    # Should handle 2000 attempts without computing 2**2000
    result = impl.schedule(2000, 1.0, 30.0, lambda u: u)
    assert len(result) == 2000
    # All values should be finite and in [0, cap]
    for delay in result:
        assert math.isfinite(delay)
        assert 0 <= delay <= 30.0


def test_cap_less_than_base():
    """When cap < base, all ceilings should be cap."""
    result = impl.schedule(5, 10.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0, 2.0, 2.0]


def test_cap_equals_base():
    """When cap == base, all ceilings should be cap."""
    result = impl.schedule(3, 5.0, 5.0, lambda u: u)
    assert result == [5.0, 5.0, 5.0]


def test_negative_attempts():
    """attempts < 0 raises ValueError with 'attempts' in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(-1, 0.2, 5.0, lambda u: u)
    assert "attempts" in str(exc_info.value)


def test_base_zero():
    """base == 0 raises ValueError with 'base' in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 0.0, 5.0, lambda u: u)
    assert "base" in str(exc_info.value)


def test_base_negative():
    """base < 0 raises ValueError with 'base' in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, -1.0, 5.0, lambda u: u)
    assert "base" in str(exc_info.value)


def test_base_infinity():
    """base == inf raises ValueError with 'base' in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, float('inf'), 5.0, lambda u: u)
    assert "base" in str(exc_info.value)


def test_base_nan():
    """base == nan raises ValueError with 'base' in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, float('nan'), 5.0, lambda u: u)
    assert "base" in str(exc_info.value)


def test_cap_zero():
    """cap == 0 raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 0.2, 0.0, lambda u: u)
    assert "cap" in str(exc_info.value)


def test_cap_infinity():
    """cap == inf raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 0.2, float('inf'), lambda u: u)
    assert "cap" in str(exc_info.value)


def test_cap_nan():
    """cap == nan raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, 0.2, float('nan'), lambda u: u)
    assert "cap" in str(exc_info.value)


def test_validation_order_attempts_before_base():
    """Validation happens in order: attempts, then base, then cap."""
    # If both attempts and base are invalid, attempts error comes first
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(-1, -1.0, 5.0, lambda u: u)
    assert "attempts" in str(exc_info.value)


def test_validation_order_base_before_cap():
    """Validation happens in order: attempts, then base, then cap."""
    # If both base and cap are invalid, base error comes first
    with pytest.raises(ValueError) as exc_info:
        impl.schedule(1, -1.0, -5.0, lambda u: u)
    assert "base" in str(exc_info.value)


def test_rand_call_count_and_arguments():
    """Verify rand is called exactly once per attempt with correct ceiling."""
    calls = []
    def tracking_rand(upper):
        calls.append(upper)
        return 0.0
    
    result = impl.schedule(4, 0.5, 4.0, tracking_rand)
    
    # Should be called 4 times
    assert len(calls) == 4
    # Ceilings should be: 0.5, 1.0, 2.0, 4.0
    assert calls == [0.5, 1.0, 2.0, 4.0]


def test_rand_values_used_unchanged():
    """Verify that rand return values are used unchanged in the result."""
    test_values = [0.1, 0.25, 0.5, 1.5]
    index = [0]
    
    def returning_rand(upper):
        val = test_values[index[0]]
        index[0] += 1
        return val
    
    result = impl.schedule(4, 0.5, 4.0, returning_rand)
    assert result == test_values
