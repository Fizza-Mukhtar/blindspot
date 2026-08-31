import hashlib

import pytest

import impl


def _expected_bucket(flag_key, user_id):
    material = f"{flag_key}:{user_id}".encode("utf-8")
    return int(hashlib.sha256(material).hexdigest(), 16) % 100


PAIRS = [
    ("checkout-v2", "user-1042"),
    ("search-rerank", "user-1042"),
    ("", ""),
    ("flag-a", "alice"),
    ("flag-b", "bob"),
    ("another-flag", "user-9999"),
    ("\u00e9moji-flag", "\u4f7f\u7528\u8005"),
]


def test_worked_example_checkout_v2_boundary():
    assert impl.is_enabled("checkout-v2", "user-1042", 19) is False
    assert impl.is_enabled("checkout-v2", "user-1042", 20) is True


def test_worked_example_search_rerank():
    assert impl.is_enabled("search-rerank", "user-1042", 10) is False
    assert impl.is_enabled("search-rerank", "user-1042", 11) is True


def test_worked_example_empty_strings():
    assert impl.is_enabled("", "", 35) is False
    assert impl.is_enabled("", "", 36) is True


def test_boundary_matches_independently_computed_bucket():
    for flag_key, user_id in PAIRS:
        bucket = _expected_bucket(flag_key, user_id)
        assert impl.is_enabled(flag_key, user_id, bucket) is False
        if bucket + 1 <= 100:
            assert impl.is_enabled(flag_key, user_id, bucket + 1) is True


def test_percentage_zero_disables_everyone():
    for flag_key, user_id in PAIRS:
        assert impl.is_enabled(flag_key, user_id, 0) is False


def test_percentage_hundred_enables_everyone():
    for flag_key, user_id in PAIRS:
        assert impl.is_enabled(flag_key, user_id, 100) is True


def test_return_value_is_actual_bool():
    result_true = impl.is_enabled("checkout-v2", "user-1042", 20)
    result_false = impl.is_enabled("checkout-v2", "user-1042", 19)
    assert isinstance(result_true, bool)
    assert isinstance(result_false, bool)


def test_purity_same_args_same_answer():
    for flag_key, user_id in PAIRS:
        first = impl.is_enabled(flag_key, user_id, 42)
        second = impl.is_enabled(flag_key, user_id, 42)
        assert first == second


def test_monotonicity_across_full_sweep():
    percentages = [0, 1, 5, 10, 19, 20, 35, 36, 50, 99, 100]
    for flag_key, user_id in PAIRS:
        results = [impl.is_enabled(flag_key, user_id, p) for p in percentages]
        seen_true = False
        for value in results:
            if seen_true:
                assert value is True
            if value:
                seen_true = True


def test_ramping_only_adds_users_never_removes():
    users = [f"user-{i}" for i in range(50)]
    lower = {u for u in users if impl.is_enabled("checkout-v2", u, 10)}
    higher = {u for u in users if impl.is_enabled("checkout-v2", u, 40)}
    assert lower.issubset(higher)


def test_bucket_does_not_depend_on_percentage():
    # Same flag/user should map to a set membership consistent with a single
    # fixed bucket regardless of which percentage triggered enrollment.
    flag_key, user_id = "checkout-v2", "user-1042"
    bucket = _expected_bucket(flag_key, user_id)
    for p in range(0, 101):
        expected = bucket < p
        assert impl.is_enabled(flag_key, user_id, p) is expected


def test_type_error_flag_key_not_str():
    with pytest.raises(TypeError):
        impl.is_enabled(123, "user-1", 50)


def test_type_error_user_id_not_str():
    with pytest.raises(TypeError):
        impl.is_enabled("flag", 456, 50)


def test_type_error_percentage_float():
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", 50.0)


def test_type_error_percentage_bool_true_and_false():
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", True)
    with pytest.raises(TypeError):
        impl.is_enabled("flag", "user", False)


def test_value_error_percentage_out_of_range():
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", -1)
    with pytest.raises(ValueError):
        impl.is_enabled("flag", "user", 101)


def test_type_checked_before_range():
    with pytest.raises(TypeError):
        impl.is_enabled("f", "u", 101.0)


def test_non_ascii_identifiers_do_not_crash_and_are_deterministic():
    flag_key = "\u00e9moji-flag"
    user_id = "\u4f7f\u7528\u8005"
    bucket = _expected_bucket(flag_key, user_id)
    result_low = impl.is_enabled(flag_key, user_id, bucket)
    result_high = impl.is_enabled(flag_key, user_id, min(bucket + 1, 100))
    assert isinstance(result_low, bool)
    assert result_low is False
    assert result_high is True
