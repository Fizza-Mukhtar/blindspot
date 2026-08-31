"""Authoritative examples for FLAG-238.

Every assertion here is traceable either to an explicit sentence of SPEC.md or
to the cited authority, not to whatever the reference implementation happens to
do.  ``make verify-corpus`` runs this against ``reference.py`` in CI, which is
what lets the README claim that ground-truth labels are verified by
construction rather than by inspection.

Sources:
  - https://www.getunleash.io/blog/hashing-it-right-solving-a-gradual-rollout-puzzle
  - https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED
"""

import hashlib

import pytest

import impl

# A deliberately non-ASCII identifier: U+00FC, U+00E9 and a snowman U+2603.
# Its bucket only comes out right if the material is encoded as UTF-8.
UNICODE_USER = "üser-é☃"

USERS = [
    "user-0",
    "user-1",
    "user-7",
    "user-42",
    "user-1042",
    "ana@example.com",
    "",
    UNICODE_USER,
]

FLAGS = ["checkout-v2", "search-rerank", "new-nav", "billing-retry", ""]


def spec_bucket(flag_key: str, user_id: str) -> int:
    """The bucket formula, transcribed verbatim from the 'Bucketing rule' section."""
    return int(
        hashlib.sha256(f"{flag_key}:{user_id}".encode("utf-8")).hexdigest(), 16
    ) % 100


def test_worked_example_from_the_spec():
    """SPEC 'Worked example': checkout-v2 / user-1042 is bucket 19."""
    assert impl.is_enabled("checkout-v2", "user-1042", 19) is False
    assert impl.is_enabled("checkout-v2", "user-1042", 20) is True


def test_worked_example_same_user_other_flag():
    """SPEC 'Worked example': the same user under search-rerank is bucket 10."""
    assert impl.is_enabled("search-rerank", "user-1042", 10) is False
    assert impl.is_enabled("search-rerank", "user-1042", 11) is True


@pytest.mark.parametrize(
    "flag_key,user_id,bucket",
    [
        ("checkout-v2", "user-1042", 19),
        ("checkout-v2", "user-7", 96),
        ("search-rerank", "user-1042", 10),
        ("new-nav", "ana@example.com", 96),
        ("billing-retry", "user-42", 71),
    ],
)
def test_exact_pinned_bucket_values(flag_key, user_id, bucket):
    """SPEC bucketing rule steps 1-4: sha256 of 'flag:user' mod 100, enabled when bucket < percentage.

    These bucket numbers are computed from the pinned formula, independently of
    the implementation under test; the boundary pair pins both the bucket and
    the strictness of the '<' comparison.
    """
    assert spec_bucket(flag_key, user_id) == bucket  # guards the literal itself
    assert impl.is_enabled(flag_key, user_id, bucket) is False
    assert impl.is_enabled(flag_key, user_id, bucket + 1) is True


def test_agrees_with_the_pinned_formula_across_a_grid():
    """SPEC bucketing rule step 3: the digest is SHA-256 over the UTF-8 bytes."""
    for flag_key in FLAGS:
        for user_id in USERS:
            expected_bucket = spec_bucket(flag_key, user_id)
            for percentage in (0, 1, 25, 50, 75, 99, 100):
                assert impl.is_enabled(flag_key, user_id, percentage) is (
                    expected_bucket < percentage
                )


def test_percentage_zero_disables_everyone():
    """SPEC 'Percentage boundaries': percentage 0 disables everyone, no bucket is < 0."""
    for flag_key in FLAGS:
        for user_id in USERS:
            assert impl.is_enabled(flag_key, user_id, 0) is False


def test_percentage_hundred_enables_everyone():
    """SPEC 'Percentage boundaries': buckets are 0-99, so every bucket is < 100."""
    for flag_key in FLAGS:
        for user_id in USERS:
            assert impl.is_enabled(flag_key, user_id, 100) is True


def test_monotonic_over_the_whole_ramp():
    """SPEC 'Monotonicity': enabled at p implies enabled at every q > p.

    This is the property the Unleash write-up calls a monotonic gradual
    rollout; salting the hash with the percentage or re-hashing per ramp step
    breaks it.
    """
    for flag_key in FLAGS:
        for user_id in USERS:
            ramp = [impl.is_enabled(flag_key, user_id, p) for p in range(0, 101)]
            for p in range(1, 101):
                assert ramp[p] or not ramp[p - 1], (
                    f"{flag_key}/{user_id} was enabled at {p - 1} but off at {p}"
                )
            # Equivalently: False sorts before True, so a monotonic ramp is
            # already sorted and flips at most once, from off to on.
            assert ramp == sorted(ramp)


def test_enabled_cohort_only_grows_as_the_flag_ramps():
    """SPEC 'Monotonicity': ramping a flag up may only ever add users."""
    previous: set[str] = set()
    for percentage in range(0, 101):
        current = {u for u in USERS if impl.is_enabled("checkout-v2", u, percentage)}
        assert previous <= current
        previous = current


def test_assignment_does_not_depend_on_the_percentage():
    """SPEC bucketing rule step 1: 'no percentage' in the hash material.

    A user's flip point must be a single threshold, so the ramp for a fixed
    pair is fully described by one bucket number.
    """
    for user_id in USERS:
        bucket = spec_bucket("new-nav", user_id)
        assert [impl.is_enabled("new-nav", user_id, p) for p in range(0, 101)] == [
            bucket < p for p in range(0, 101)
        ]


def test_material_is_the_two_ids_joined_by_a_single_colon():
    """SPEC bucketing rule step 1: the material is exactly f'{flag_key}:{user_id}'.

    Both halves below produce the material 'a:b:c', so they must agree at every
    percentage.
    """
    for percentage in range(0, 101):
        assert impl.is_enabled("a:b", "c", percentage) == impl.is_enabled(
            "a", "b:c", percentage
        )
    assert impl.is_enabled("a:b", "c", 6) is False
    assert impl.is_enabled("a:b", "c", 7) is True


def test_non_ascii_identifiers_are_encoded_as_utf8():
    """SPEC bucketing rule step 2 and 'Errors': non-ASCII identifiers are legitimate."""
    assert spec_bucket("billing-retry", UNICODE_USER) == 54
    assert impl.is_enabled("billing-retry", UNICODE_USER, 54) is False
    assert impl.is_enabled("billing-retry", UNICODE_USER, 55) is True


def test_empty_identifiers_are_permitted_and_hash_normally():
    """SPEC 'Errors': an empty flag_key or user_id is not an error; ':' is bucket 35."""
    assert impl.is_enabled("", "", 35) is False
    assert impl.is_enabled("", "", 36) is True
    assert impl.is_enabled("", "user-42", 94) is False
    assert impl.is_enabled("", "user-42", 95) is True
    assert impl.is_enabled("checkout-v2", "", 54) is False
    assert impl.is_enabled("checkout-v2", "", 55) is True


def test_returns_an_actual_bool():
    """SPEC 'What to build': the returned value must be an actual bool."""
    assert type(impl.is_enabled("checkout-v2", "user-42", 50)) is bool
    assert type(impl.is_enabled("checkout-v2", "user-42", 0)) is bool


def test_result_is_stable_across_repeated_calls():
    """SPEC 'What to build': same arguments, same answer, in any process.

    A per-process salt (the builtin hash(), documented at the PYTHONHASHSEED
    link) cannot be caught inside one process, but an implementation that
    memoises or mutates state can be.
    """
    first = [impl.is_enabled("new-nav", u, 40) for u in USERS]
    second = [impl.is_enabled("new-nav", u, 40) for u in USERS]
    assert first == second


@pytest.mark.parametrize("percentage", [-1, 101, -100, 1000, -(10**9), 10**9])
def test_out_of_range_percentage_raises_value_error(percentage):
    """SPEC 'Errors': an int percentage outside the inclusive 0-100 range raises ValueError."""
    with pytest.raises(ValueError):
        impl.is_enabled("checkout-v2", "user-42", percentage)


@pytest.mark.parametrize("percentage", [50.0, 0.0, 100.0, "50", None, True, False, (50,)])
def test_non_int_percentage_raises_type_error(percentage):
    """SPEC 'Errors': non-int percentage raises TypeError, including float and bool."""
    with pytest.raises(TypeError):
        impl.is_enabled("checkout-v2", "user-42", percentage)


@pytest.mark.parametrize("bad", [None, 42, b"user-42", ["user-42"], 3.5])
def test_non_str_identifiers_raise_type_error(bad):
    """SPEC 'Errors': a flag_key or user_id that is not a str raises TypeError."""
    with pytest.raises(TypeError):
        impl.is_enabled(bad, "user-42", 50)
    with pytest.raises(TypeError):
        impl.is_enabled("checkout-v2", bad, 50)


def test_type_check_precedes_range_check():
    """SPEC 'Errors': is_enabled('f', 'u', 101.0) raises TypeError, not ValueError."""
    with pytest.raises(TypeError):
        impl.is_enabled("f", "u", 101.0)
    with pytest.raises(TypeError):
        impl.is_enabled("f", "u", -1.0)
