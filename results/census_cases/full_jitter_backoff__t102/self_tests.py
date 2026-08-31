import math
import impl
import pytest


def test_attempts_zero():
    """attempts == 0 returns an empty list."""
    result = impl.schedule(0, 1.0, 1.0, lambda u: u)
    assert result == []


def test_attempts_negative():
    """attempts < 0 raises ValueError with 'attempts' in message."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 1.0, 1.0, lambda u: u)


def test_base_zero():
    """base == 0 raises ValueError with 'base' in message."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, 0.0, 1.0, lambda u: u)


def test_base_negative():
    """base < 0 raises ValueError with 'base' in message."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, -1.0, 1.0, lambda u: u)


def test_base_inf():
    """base == inf raises ValueError with 'base' in message."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, float('inf'), 1.0, lambda u: u)


def test_base_nan():
    """base == nan raises ValueError with 'base' in message."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, float('nan'), 1.0, lambda u: u)


def test_cap_zero():
    """cap == 0 raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, 0.0, lambda u: u)


def test_cap_negative():
    """cap < 0 raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, -1.0, lambda u: u)


def test_cap_inf():
    """cap == inf raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, float('inf'), lambda u: u)


def test_cap_nan():
    """cap == nan raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(1, 1.0, float('nan'), lambda u: u)


def test_validation_order_attempts_first():
    """Validation order: attempts checked before base/cap errors."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 0.0, 0.0, lambda u: u)


def test_validation_order_base_before_cap():
    """Validation order: base checked before cap errors."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(1, 0.0, 0.0, lambda u: u)


def test_example_from_ticket():
    """Verify the documented example: base=0.2, cap=5.0, attempts=6, rand=lambda u: u/2."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
    assert result == expected


def test_cap_less_than_base():
    """cap < base is valid; all ceilings are capped to cap."""
    result = impl.schedule(3, 10.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0]


def test_cap_equals_base():
    """cap == base is valid; all ceilings are the same."""
    result = impl.schedule(3, 2.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0]


def test_exponential_growth_until_cap():
    """Verify exponential growth of ceilings until cap is reached."""
    result = impl.schedule(5, 1.0, 20.0, lambda u: u)
    assert result == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_exponential_growth_with_cap_clamp():
    """Verify clamping to cap after exponential growth."""
    result = impl.schedule(7, 1.0, 10.0, lambda u: u)
    assert result == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0, 10.0]


def test_large_attempts_no_overflow():
    """2000 attempts with base=1.0, cap=30.0 should not overflow."""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: 0.0)
    assert len(result) == 2000
    assert all(x == 0.0 for x in result)


def test_rand_called_once_per_attempt():
    """rand should be called exactly once per attempt."""
    call_count = [0]
    
    def counting_rand(upper):
        call_count[0] += 1
        return 0.0
    
    impl.schedule(5, 1.0, 100.0, counting_rand)
    assert call_count[0] == 5


def test_rand_receives_correct_ceilings():
    """Verify rand receives the correct ceiling values."""
    received_ceilings = []
    
    def recording_rand(upper):
        received_ceilings.append(upper)
        return 0.0
    
    impl.schedule(5, 1.0, 10.0, recording_rand)
    assert received_ceilings == [1.0, 2.0, 4.0, 8.0, 10.0]
