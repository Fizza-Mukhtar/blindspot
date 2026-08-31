import hashlib
import impl
import pytest


def compute_bucket(flag_key: str, user_id: str) -> int:
    """Helper to compute bucket for a given flag_key and user_id."""
    material = f"{flag_key}:{user_id}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    return int(digest, 16) % 100


def test_is_enabled_bucket_boundary():
    """User enabled when bucket < percentage, disabled when bucket >= percentage."""
    flag_key, user_id = "test-flag", "user-1"
    bucket = compute_bucket(flag_key, user_id)
    
    # At percentage > bucket, should be enabled
    assert impl.is_enabled(flag_key, user_id, bucket + 1) is True
    # At percentage == bucket, should be disabled
    assert impl.is_enabled(flag_key, user_id, bucket) is False


def test_is_enabled_various_percentages():
    """Test with various percentages to ensure correct bucket comparison."""
    flag_key, user_id = "flag", "user"
    bucket = compute_bucket(flag_key, user_id)
    
    # Test various percentages
    for pct in [0, 25, 50, 75, 100]:
        expected = bucket < pct
        assert impl.is_enabled(flag_key, user_id, pct) is expected


def test_percentage_0_disables_all():
    """0% disables everyone (no bucket < 0)."""
    assert impl.is_enabled("flag", "user", 0) is False
    assert impl.is_enabled("test", "anyone", 0) is False
    assert impl.is_enabled("", "", 0) is False


def test_percentage_100_enables_all():
    """100% enables everyone (all buckets < 100)."""
    assert impl.is_enabled("flag", "user", 100) is True
    assert impl.is_enabled("test", "anyone", 100) is True
    assert impl.is_enabled("", "", 100) is True


def test_known_test_case():
    """Test the documented example: checkout-v2:user-1042 is bucket 19."""
    bucket = compute_bucket("checkout-v2", "user-1042")
    assert bucket == 19
    
    # Off at 19, on at 20
    assert impl.is_enabled("checkout-v2", "user-1042", 19) is False
    assert impl.is_enabled("checkout-v2", "user-1042", 20) is True


def test_empty_flag_key():
    """Empty flag_key is legitimate and hashes normally."""
    bucket = compute_bucket("", "user-123")
    assert impl.is_enabled("", "user-123", bucket + 1) is True
    assert impl.is_enabled("", "user-123", bucket) is False


def test_empty_user_id():
    """Empty user_id is legitimate (e.g., for anonymous sessions)."""
    bucket = compute_bucket("flag", "")
    assert impl.is_enabled("flag", "", bucket + 1) is True
    assert impl.is_enabled("flag", "", bucket) is False


def test_both_empty_identifiers():
    """Both flag_key and user_id can be empty."""
    bucket = compute_bucket("", "")
    assert impl.is_enabled("", "", bucket + 1) is True
    assert impl.is_enabled("", "", bucket) is False


def test_non_ascii_identifiers():
    """Non-ASCII identifiers are handled via UTF-8 encoding."""
    bucket = compute_bucket("flag-🚀", "user-你好")
    assert impl.is_enabled("flag-🚀", "user-你好", bucket + 1) is True
    assert impl.is_enabled("flag-🚀", "user-你好", bucket) is False


def test_idempotent():
    """Same arguments produce the same result across multiple calls."""
    result1 = impl.is_enabled("flag", "user", 50)
    result2 = impl.is_enabled("flag", "user", 50)
    result3 = impl.is_enabled("flag", "user", 50)
    assert result1 is result2
    assert result2 is result3


def test_deterministic_different_contexts():
    """Results are deterministic regardless of other operations."""
    result1 = impl.is_enabled("x", "y", 25)
    
    # Do some other operations
    _ = impl.is_enabled("a", "b", 75)
    _ = impl.is_enabled("p", "q", 50)
    
    # Same arguments should produce same result
    result2 = impl.is_enabled("x", "y", 25)
    assert result1 is result2


def test_flag_key_not_str_type_error():
    """Non-str flag_key raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled(123, "user", 50)
    with pytest.raises(TypeError):
        impl.is_enabled(None, "user", 50)


def test_user_id_not_str_type_error():
    """Non-str user_id raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", 456, 50)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", None, 50)


def test_percentage_not_int_float_type_error():
    """Float percentage raises TypeError, even if integral value."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 50.0)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 50.5)


def test_percentage_bool_type_error():
    """Bool percentage raises TypeError (even though bool is subclass of int)."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", True)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", False)


def test_percentage_out_of_range_value_error():
    """Percentage outside [0, 100] raises ValueError."""
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", -1)
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", 101)


def test_type_error_before_value_error():
    """Type errors take precedence over value errors."""
    # Invalid type (float) with invalid value (101.0)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 101.0)
