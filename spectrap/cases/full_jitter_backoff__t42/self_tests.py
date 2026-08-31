import impl
import pytest
import math


def test_empty_schedule():
    """attempts == 0 returns empty list."""
    result = impl.schedule(0, 1.0, 10.0, lambda u: u)
    assert result == []


def test_single_attempt():
    """attempts == 1 returns single delay."""
    result = impl.schedule(1, 1.0, 10.0, lambda u: u / 2)
    assert result == [0.5]


def test_ticket_example():
    """Test example from ticket: base=0.2, cap=5.0, attempts=6 with rand=u/2."""
    result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
    expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
    assert result == expected


def test_identity_rand():
    """With identity rand, delays equal ceilings."""
    result = impl.schedule(3, 1.0, 10.0, lambda u: u)
    assert result == [1.0, 2.0, 4.0]


def test_zero_rand():
    """With zero rand, all delays are zero."""
    result = impl.schedule(5, 0.5, 5.0, lambda u: 0.0)
    assert result == [0.0, 0.0, 0.0, 0.0, 0.0]


def test_cap_clamping():
    """Ceilings clamp at cap once base * 2**i >= cap."""
    result = impl.schedule(5, 1.0, 5.0, lambda u: u)
    # Once exponential >= cap, power_of_2 stops incrementing
    assert result == [1.0, 2.0, 4.0, 5.0, 5.0]


def test_cap_equals_base():
    """When cap == base, all ceilings are cap (flat fully jittered)."""
    result = impl.schedule(4, 2.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0, 2.0]


def test_cap_less_than_base():
    """When cap < base, all ceilings are cap."""
    result = impl.schedule(3, 5.0, 2.0, lambda u: u)
    assert result == [2.0, 2.0, 2.0]


def test_large_attempts():
    """Large number of attempts doesn't overflow or raise."""
    result = impl.schedule(2000, 1.0, 30.0, lambda u: 0.0)
    assert len(result) == 2000
    assert all(d == 0.0 for d in result)


def test_small_values():
    """Small floating point values work correctly."""
    result = impl.schedule(3, 0.01, 0.1, lambda u: u)
    assert result == [0.01, 0.02, 0.04]


def test_rand_tracking():
    """Verify rand is called once per attempt with correct ceilings in order."""
    calls = []
    def tracking_rand(u):
        calls.append(u)
        return u * 0.1
    
    result = impl.schedule(3, 1.0, 8.0, tracking_rand)
    assert calls == [1.0, 2.0, 4.0]
    assert result == [0.1, 0.2, 0.4]


def test_attempts_negative():
    """Negative attempts raises ValueError with 'attempts' in message."""
    with pytest.raises(ValueError, match="attempts"):
        impl.schedule(-1, 1.0, 10.0, lambda u: u)


def test_base_zero():
    """base == 0 raises ValueError with 'base' in message."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, 0.0, 10.0, lambda u: u)


def test_base_negative():
    """base < 0 raises ValueError with 'base' in message."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, -1.0, 10.0, lambda u: u)


def test_base_infinity():
    """base == inf raises ValueError with 'base' in message."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, float('inf'), 10.0, lambda u: u)


def test_base_nan():
    """base == nan raises ValueError (isfinite catches nan)."""
    with pytest.raises(ValueError, match="base"):
        impl.schedule(5, float('nan'), 10.0, lambda u: u)


def test_cap_zero():
    """cap == 0 raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(5, 1.0, 0.0, lambda u: u)


def test_cap_negative():
    """cap < 0 raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(5, 1.0, -5.0, lambda u: u)


def test_cap_infinity():
    """cap == inf raises ValueError with 'cap' in message."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(5, 1.0, float('inf'), lambda u: u)


def test_cap_nan():
    """cap == nan raises ValueError (isfinite catches nan)."""
    with pytest.raises(ValueError, match="cap"):
        impl.schedule(5, 1.0, float('nan'), lambda u: u)
