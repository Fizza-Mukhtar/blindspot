import pytest
import impl


def test_known_hash_value_bucket_19_disabled():
    """checkout-v2:user-1042 should be bucket 19, so disabled at percentage 19"""
    assert impl.is_enabled("checkout-v2", "user-1042", 19) is False


def test_known_hash_value_bucket_19_enabled():
    """checkout-v2:user-1042 should be bucket 19, so enabled at percentage 20"""
    assert impl.is_enabled("checkout-v2", "user-1042", 20) is True


def test_consistency_same_arguments_same_result():
    """Same arguments should always produce the same result (deterministic)"""
    result1 = impl.is_enabled("flag1", "user1", 50)
    result2 = impl.is_enabled("flag1", "user1", 50)
    assert result1 is result2


def test_percentage_0_disables_everyone():
    """At 0%, no one is enabled (no bucket is < 0)"""
    assert impl.is_enabled("any", "any", 0) is False
    assert impl.is_enabled("", "", 0) is False
    assert impl.is_enabled("x", "y", 0) is False


def test_percentage_100_enables_everyone():
    """At 100%, everyone is enabled (all buckets 0-99 are < 100)"""
    assert impl.is_enabled("any", "any", 100) is True
    assert impl.is_enabled("", "", 100) is True
    assert impl.is_enabled("x", "y", 100) is True


def test_empty_flag_key_is_valid():
    """Empty flag_key is legitimate and hashes like any other string"""
    result = impl.is_enabled("", "user1", 50)
    assert isinstance(result, bool)


def test_empty_user_id_is_valid():
    """Empty user_id is legitimate for anonymous sessions"""
    result = impl.is_enabled("flag1", "", 50)
    assert isinstance(result, bool)


def test_non_ascii_identifiers_are_supported():
    """Non-ASCII identifiers are supported via UTF-8 encoding"""
    result = impl.is_enabled("flag-日本語", "user-🎉", 50)
    assert isinstance(result, bool)


def test_different_flags_produce_different_buckets():
    """Different flags can assign the same user to different buckets"""
    r1 = impl.is_enabled("flag1", "user1", 50)
    r2 = impl.is_enabled("flag2", "user1", 50)
    assert isinstance(r1, bool) and isinstance(r2, bool)


def test_type_error_non_str_flag_key():
    """Non-str flag_key raises TypeError"""
    with pytest.raises(TypeError):
        impl.is_enabled(123, "user1", 50)
    with pytest.raises(TypeError):
        impl.is_enabled(None, "user1", 50)


def test_type_error_non_str_user_id():
    """Non-str user_id raises TypeError"""
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", 123, 50)
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", None, 50)


def test_type_error_float_percentage():
    """Float percentage raises TypeError, including integral floats like 50.0"""
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", "user1", 50.0)
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", "user1", 50.5)


def test_type_error_bool_percentage():
    """Bool percentage raises TypeError (bool is subclass of int but not valid)"""
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", "user1", True)
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", "user1", False)


def test_type_error_non_numeric_percentage():
    """Non-numeric percentage raises TypeError"""
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", "user1", "50")
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", "user1", None)


def test_value_error_negative_percentage():
    """Negative percentage raises ValueError"""
    with pytest.raises(ValueError):
        impl.is_enabled("flag1", "user1", -1)
    with pytest.raises(ValueError):
        impl.is_enabled("flag1", "user1", -100)


def test_value_error_percentage_over_100():
    """Percentage > 100 raises ValueError"""
    with pytest.raises(ValueError):
        impl.is_enabled("flag1", "user1", 101)
    with pytest.raises(ValueError):
        impl.is_enabled("flag1", "user1", 200)


def test_type_error_raised_before_value_error():
    """Type errors are checked before range errors (101.0 is TypeError, not ValueError)"""
    with pytest.raises(TypeError):
        impl.is_enabled("flag1", "user1", 101.0)


def test_returns_actual_bool_type():
    """Return value is actual bool type, not just truthy/falsy value"""
    result_true = impl.is_enabled("flag1", "user1", 100)
    result_false = impl.is_enabled("flag1", "user1", 0)
    assert result_true is True
    assert result_false is False
    assert type(result_true) is bool
    assert type(result_false) is bool
