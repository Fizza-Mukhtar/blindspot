import impl
import hashlib
import pytest


def test_returns_actual_bool():
    """Return value should be actual bool type."""
    result = impl.is_enabled("flag", "user", 50)
    assert result is True or result is False
    assert type(result) is bool


def test_specific_example_bucket_19_at_19_percent():
    """Ticket example: checkout-v2:user-1042 buckets to 19, disabled at 19%."""
    # Verify bucket is 19
    material = "checkout-v2:user-1042"
    bucket = int(hashlib.sha256(material.encode("utf-8")).hexdigest(), 16) % 100
    assert bucket == 19
    
    # User is disabled when bucket >= percentage (19 >= 19)
    assert impl.is_enabled("checkout-v2", "user-1042", 19) is False


def test_specific_example_bucket_19_at_20_percent():
    """Ticket example: checkout-v2:user-1042 enabled at 20%."""
    # User is enabled when bucket < percentage (19 < 20)
    assert impl.is_enabled("checkout-v2", "user-1042", 20) is True


def test_zero_percent_disables_everyone():
    """At 0%, no buckets satisfy bucket < 0."""
    assert impl.is_enabled("any", "any", 0) is False
    assert impl.is_enabled("", "", 0) is False


def test_hundred_percent_enables_everyone():
    """At 100%, all buckets 0-99 satisfy bucket < 100."""
    assert impl.is_enabled("any", "any", 100) is True
    assert impl.is_enabled("", "", 100) is True


def test_same_inputs_same_output():
    """Determinism: identical calls return identical results."""
    for _ in range(5):
        assert impl.is_enabled("test", "user", 50) == impl.is_enabled("test", "user", 50)


def test_user_in_at_percentage_p_in_at_p_plus_1():
    """Monotonicity: if enabled at P, enabled at all P' > P."""
    flag, user = "monotone", "check"
    
    # Find first enabled percentage
    first_on = None
    for p in range(101):
        if impl.is_enabled(flag, user, p):
            first_on = p
            break
    
    # If found, verify monotonicity
    if first_on is not None:
        for p in range(first_on):
            assert impl.is_enabled(flag, user, p) is False
        for p in range(first_on, 101):
            assert impl.is_enabled(flag, user, p) is True


def test_empty_identifiers_are_valid():
    """Empty strings are legitimate identifiers (e.g., anonymous sessions)."""
    # Should not raise
    impl.is_enabled("", "", 50)
    impl.is_enabled("flag", "", 50)
    impl.is_enabled("", "user", 50)


def test_non_ascii_identifiers():
    """Non-ASCII characters in identifiers work via UTF-8 encoding."""
    result = impl.is_enabled("flag-Ὠ0", "user-中文", 50)
    assert isinstance(result, bool)


def test_flag_key_type_error():
    """flag_key must be str; non-str raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled(123, "user", 50)
    with pytest.raises(TypeError):
        impl.is_enabled(None, "user", 50)


def test_user_id_type_error():
    """user_id must be str; non-str raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", 456, 50)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", None, 50)


def test_percentage_float_type_error():
    """percentage must be int, not float (even integral ones like 50.0)."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 50.0)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 75.5)


def test_percentage_bool_type_error():
    """percentage must not be bool (isinstance(bool, int) is True in Python)."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", True)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", False)


def test_percentage_non_int_type_error():
    """percentage must be int."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", "50")
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", [50])


def test_type_error_before_range_error():
    """Type checking occurs before range checking."""
    # 101.0 should raise TypeError (not int), not ValueError (out of range)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 101.0)


def test_percentage_negative_value_error():
    """percentage < 0 raises ValueError after type checks pass."""
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", -1)
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", -50)


def test_percentage_over_100_value_error():
    """percentage > 100 raises ValueError after type checks pass."""
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", 101)
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", 200)
