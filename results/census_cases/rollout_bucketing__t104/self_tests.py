import pytest
import impl


def test_basic_enabled():
    """Test that a user can be enabled for a flag."""
    result = impl.is_enabled("flag1", "user1", 50)
    assert isinstance(result, bool)


def test_percentage_zero_disables_everyone():
    """At 0%, no user should be enabled."""
    assert impl.is_enabled("flag", "user1", 0) is False
    assert impl.is_enabled("flag", "user2", 0) is False


def test_percentage_100_enables_everyone():
    """At 100%, all users should be enabled."""
    assert impl.is_enabled("flag", "user1", 100) is True
    assert impl.is_enabled("flag", "user2", 100) is True


def test_known_bucket_checkout_v2():
    """Test the specific example from the ticket."""
    # "checkout-v2:user-1042" should have bucket 19
    # So it should be off at 19, on at 20
    assert impl.is_enabled("checkout-v2", "user-1042", 19) is False
    assert impl.is_enabled("checkout-v2", "user-1042", 20) is True


def test_deterministic_same_input_same_output():
    """Same inputs always produce same output."""
    r1 = impl.is_enabled("flag", "user", 50)
    r2 = impl.is_enabled("flag", "user", 50)
    r3 = impl.is_enabled("flag", "user", 50)
    assert r1 == r2 == r3


def test_empty_identifiers_work():
    """Empty identifiers are legitimate (analytics use case)."""
    r1 = impl.is_enabled("flag", "", 50)
    r2 = impl.is_enabled("", "user", 50)
    r3 = impl.is_enabled("", "", 50)
    assert isinstance(r1, bool)
    assert isinstance(r2, bool)
    assert isinstance(r3, bool)


def test_unicode_identifiers():
    """Non-ASCII identifiers should work."""
    r1 = impl.is_enabled("🚀flag", "user", 50)
    r2 = impl.is_enabled("flag", "用户", 50)
    r3 = impl.is_enabled("флаг", "юзер", 75)
    assert isinstance(r1, bool)
    assert isinstance(r2, bool)
    assert isinstance(r3, bool)


def test_flag_key_type_error():
    """flag_key must be str."""
    with pytest.raises(TypeError):
        impl.is_enabled(123, "user", 50)
    with pytest.raises(TypeError):
        impl.is_enabled(None, "user", 50)
    with pytest.raises(TypeError):
        impl.is_enabled(["flag"], "user", 50)


def test_user_id_type_error():
    """user_id must be str."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", 123, 50)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", None, 50)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", ["user"], 50)


def test_percentage_type_error_float():
    """percentage must be int, not float, even integral floats."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 50.0)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 100.0)


def test_percentage_type_error_string():
    """percentage must be int, not str."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", "50")


def test_percentage_type_error_bool():
    """percentage must be int, not bool (even though bool is subclass of int)."""
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", True)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", False)


def test_type_error_before_range_error():
    """Type errors raised before range errors."""
    # 101.0 is both out of range and wrong type, should raise TypeError
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 101.0)
    # -1.5 is both out of range and wrong type, should raise TypeError
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", -1.5)


def test_percentage_range_error():
    """percentage must be in 0-100 inclusive."""
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", -1)
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", -100)
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", 101)
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", 200)


def test_percentage_boundaries_valid():
    """Boundaries 0 and 100 are valid and should not raise."""
    impl.is_enabled("flag", "user", 0)
    impl.is_enabled("flag", "user", 100)


def test_rollout_widening():
    """Users enabled at percentage P are still enabled at P+1."""
    flag = "feature"
    user = "testuser"
    
    # For each percentage, check that if enabled at P, then enabled at P+1
    for p in range(100):
        enabled_at_p = impl.is_enabled(flag, user, p)
        enabled_at_p_plus_1 = impl.is_enabled(flag, user, p + 1)
        if enabled_at_p:
            assert enabled_at_p_plus_1, \
                f"User enabled at {p}% but not at {p+1}% violates rollout widening"


def test_return_type_is_bool():
    """Function returns actual bool type, not just truthy/falsy."""
    r1 = impl.is_enabled("checkout-v2", "user-1042", 100)
    r2 = impl.is_enabled("checkout-v2", "user-1042", 0)
    assert type(r1) is bool
    assert type(r2) is bool
    assert r1 is True
    assert r2 is False
