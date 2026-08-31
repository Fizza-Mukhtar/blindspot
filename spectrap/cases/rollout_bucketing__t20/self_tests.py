import hashlib
import pytest
import impl


def test_basic_enabled():
    """User enabled when bucket < percentage."""
    result = impl.is_enabled("checkout-v2", "user-1042", 20)
    assert result is True


def test_basic_disabled():
    """User disabled when bucket >= percentage."""
    result = impl.is_enabled("checkout-v2", "user-1042", 19)
    assert result is False


def test_percentage_zero():
    """At 0%, no user is enabled."""
    assert impl.is_enabled("flag", "user", 0) is False


def test_percentage_100():
    """At 100%, all users are enabled."""
    assert impl.is_enabled("flag", "user", 100) is True


def test_consistency():
    """Same input always produces same output."""
    result1 = impl.is_enabled("flag", "user", 50)
    result2 = impl.is_enabled("flag", "user", 50)
    assert result1 is result2


def test_monotonic_enabled():
    """User enabled at X% stays enabled at higher percentages."""
    assert impl.is_enabled("checkout-v2", "user-1042", 20) is True
    assert impl.is_enabled("checkout-v2", "user-1042", 50) is True
    assert impl.is_enabled("checkout-v2", "user-1042", 100) is True


def test_monotonic_disabled():
    """User disabled at X% stays disabled at lower percentages."""
    assert impl.is_enabled("checkout-v2", "user-1042", 19) is False
    assert impl.is_enabled("checkout-v2", "user-1042", 10) is False
    assert impl.is_enabled("checkout-v2", "user-1042", 0) is False


def test_empty_identifiers():
    """Empty flag_key and user_id are allowed."""
    result1 = impl.is_enabled("", "user", 50)
    assert isinstance(result1, bool)
    result2 = impl.is_enabled("flag", "", 50)
    assert isinstance(result2, bool)
    result3 = impl.is_enabled("", "", 50)
    assert isinstance(result3, bool)


def test_non_ascii_identifiers():
    """Non-ASCII identifiers work with UTF-8."""
    result1 = impl.is_enabled("\u30d5\u30e9\u30b0", "user", 50)
    assert isinstance(result1, bool)
    result2 = impl.is_enabled("flag", "\u7528\u6237", 50)
    assert isinstance(result2, bool)


def test_type_error_flag_key_not_str():
    """Non-str flag_key raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled(123, "user", 50)
    with pytest.raises(TypeError):
        impl.is_enabled(None, "user", 50)


def test_type_error_user_id_not_str():
    """Non-str user_id raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", 123, 50)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", None, 50)


def test_type_error_percentage_float():
    """Float percentage raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 50.0)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 50.5)


def test_type_error_percentage_bool():
    """Bool percentage raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", True)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", False)


def test_type_error_percentage_string():
    """String percentage raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", "50")


def test_value_error_percentage_negative():
    """Negative percentage raises ValueError."""
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", -1)


def test_value_error_percentage_over_100():
    """Percentage > 100 raises ValueError."""
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", 101)


def test_type_before_range_check():
    """Type check happens before range check."""
    with pytest.raises(TypeError):
        impl.is_enabled("f", "u", 101.0)
