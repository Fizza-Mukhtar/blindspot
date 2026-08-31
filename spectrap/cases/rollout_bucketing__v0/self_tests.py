import hashlib

import pytest

import impl


def _bucket(flag_key, user_id):
    material = f"{flag_key}:{user_id}".encode("utf-8")
    return int(hashlib.sha256(material).hexdigest(), 16) % 100


def test_worked_example_checkout_v2_boundary():
    # bucket for checkout-v2:user-1042 is 19 per the ticket's worked example
    assert _bucket("checkout-v2", "user-1042") == 19
    assert impl.is_enabled("checkout-v2", "user-1042", 19) is False
    assert impl.is_enabled("checkout-v2", "user-1042", 20) is True


def test_worked_example_search_rerank():
    # same user, different flag -> bucket 10, already enabled at 11%
    assert _bucket("search-rerank", "user-1042") == 10
    assert impl.is_enabled("search-rerank", "user-1042", 10) is False
    assert impl.is_enabled("search-rerank", "user-1042", 11) is True


def test_empty_strings_boundary():
    # ":" hashes to bucket 35 per the ticket
    assert _bucket("", "") == 35
    assert impl.is_enabled("", "", 36) is True
    assert impl.is_enabled("", "", 35) is False


def test_percentage_zero_disables_everyone():
    ids = ["a", "b", "user-1042", "user-9999", "anon-session-0", "", "z" * 50]
    for uid in ids:
        assert impl.is_enabled("any-flag", uid, 0) is False


def test_percentage_100_enables_everyone():
    ids = ["a", "b", "user-1042", "user-9999", "anon-session-0", "", "z" * 50]
    for uid in ids:
        assert impl.is_enabled("any-flag", uid, 100) is True


def test_monotonicity_property():
    flag_key = "checkout-v2"
    user_ids = ["user-1042", "user-1", "user-2", "user-3", "user-4", "user-5"]
    for uid in user_ids:
        bucket = _bucket(flag_key, uid)
        for p in range(0, 101):
            expected = bucket < p
            assert impl.is_enabled(flag_key, uid, p) == expected
        # explicit monotonic check: once True, stays True for all higher p
        seen_true = False
        for p in range(0, 101):
            result = impl.is_enabled(flag_key, uid, p)
            if seen_true:
                assert result is True
            if result:
                seen_true = True


def test_percentage_does_not_depend_on_itself():
    # bucket assignment must be identical regardless of the percentage argument
    # used to query it -- ramp steps must not reshuffle the cohort
    flag_key = "checkout-v2"
    user_id = "user-1042"
    bucket = _bucket(flag_key, user_id)
    for p in (bucket, bucket + 1, 100):
        assert impl.is_enabled(flag_key, user_id, p) is (bucket < p)


def test_deterministic_same_result():
    results = {impl.is_enabled("checkout-v2", "user-1042", 50) for _ in range(20)}
    assert len(results) == 1


def test_return_type_is_actual_bool():
    result_true = impl.is_enabled("checkout-v2", "user-1042", 100)
    result_false = impl.is_enabled("checkout-v2", "user-1042", 0)
    assert type(result_true) is bool
    assert type(result_false) is bool


def test_flag_key_not_str_raises_typeerror():
    with pytest.raises(TypeError):
        impl.is_enabled(123, "user-1042", 50)
    with pytest.raises(TypeError):
        impl.is_enabled(None, "user-1042", 50)


def test_user_id_not_str_raises_typeerror():
    with pytest.raises(TypeError):
        impl.is_enabled("checkout-v2", 1042, 50)
    with pytest.raises(TypeError):
        impl.is_enabled("checkout-v2", None, 50)


def test_percentage_float_raises_typeerror():
    with pytest.raises(TypeError):
        impl.is_enabled("checkout-v2", "user-1042", 50.0)
    with pytest.raises(TypeError):
        impl.is_enabled("checkout-v2", "user-1042", 50.5)


def test_percentage_bool_raises_typeerror():
    with pytest.raises(TypeError):
        impl.is_enabled("checkout-v2", "user-1042", True)
    with pytest.raises(TypeError):
        impl.is_enabled("checkout-v2", "user-1042", False)


def test_percentage_out_of_range_raises_valueerror():
    with pytest.raises(ValueError):
        impl.is_enabled("checkout-v2", "user-1042", -1)
    with pytest.raises(ValueError):
        impl.is_enabled("checkout-v2", "user-1042", 101)


def test_type_checked_before_range():
    # 101.0 is out of range AND wrong type; type check must win -> TypeError
    with pytest.raises(TypeError):
        impl.is_enabled("f", "u", 101.0)


def test_non_ascii_identifiers_work():
    flag_key = "caf\u00e9-flag"
    user_id = "\u30e6\u30fc\u30b6\u30fc-1"
    bucket = _bucket(flag_key, user_id)
    assert impl.is_enabled(flag_key, user_id, bucket) is False
    assert impl.is_enabled(flag_key, user_id, min(bucket + 1, 100)) is True


def test_different_flags_same_user_can_have_different_buckets():
    # sanity check that flag_key is actually part of the hash material,
    # not just user_id
    b1 = _bucket("checkout-v2", "user-1042")
    b2 = _bucket("search-rerank", "user-1042")
    assert b1 != b2
    assert impl.is_enabled("checkout-v2", "user-1042", b1 + 1) is True
    assert impl.is_enabled("search-rerank", "user-1042", b1 + 1) == (b2 < b1 + 1)
