"""Authoritative examples for RELENG-412.

Every assertion here is taken from the cited standard, not from the reference
implementation's behaviour.  ``make verify-corpus`` runs this against
``reference.py`` in CI, which is what lets the README claim that ground-truth
labels are verified by construction rather than by inspection.

Source: https://semver.org/spec/v2.0.0.html (items 9, 10, 11)
"""

import pytest

import impl


def test_spec_item_11_example_ordering():
    """The exact ordering printed in item 11 of the specification."""
    given = [
        "1.0.0",
        "1.0.0-rc.1",
        "1.0.0-beta.11",
        "1.0.0-beta.2",
        "1.0.0-beta",
        "1.0.0-alpha.beta",
        "1.0.0-alpha.1",
        "1.0.0-alpha",
    ]
    assert impl.sort_versions(given) == [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]


def test_numeric_identifier_ranks_below_alphanumeric():
    """Item 11.4.3."""
    assert impl.sort_versions(["1.0.0-alpha.beta", "1.0.0-alpha.11"]) == [
        "1.0.0-alpha.11",
        "1.0.0-alpha.beta",
    ]


def test_numeric_identifiers_compare_numerically_not_lexically():
    """Item 11.4.1 -- the bug that motivated the ticket."""
    assert impl.sort_versions(["1.0.0-rc.10", "1.0.0-rc.2"]) == [
        "1.0.0-rc.2",
        "1.0.0-rc.10",
    ]


def test_larger_identifier_set_wins_when_prefix_equal():
    """Item 11.4.4."""
    assert impl.sort_versions(["1.0.0-alpha.1", "1.0.0-alpha"]) == [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
    ]


def test_prerelease_ranks_below_the_normal_version():
    """Item 11.3."""
    assert impl.sort_versions(["1.0.0", "1.0.0-rc.1"]) == ["1.0.0-rc.1", "1.0.0"]


def test_build_metadata_is_ignored_and_ties_are_stable():
    """Item 10 plus the ticket's stability requirement."""
    given = ["1.0.0+build.99", "1.0.0+build.1", "1.0.0"]
    assert impl.sort_versions(given) == given


def test_core_numbers_compare_numerically():
    assert impl.sort_versions(["1.9.0", "1.10.0", "1.0.10", "1.0.9"]) == [
        "1.0.9",
        "1.0.10",
        "1.9.0",
        "1.10.0",
    ]


def test_ascii_order_for_alphanumeric_identifiers():
    """Item 11.4.2: 'lexically in ASCII sort order' -- 'A' (0x41) < 'a' (0x61)."""
    assert impl.sort_versions(["1.0.0-a", "1.0.0-A"]) == ["1.0.0-A", "1.0.0-a"]


def test_leading_v_is_accepted_and_preserved():
    assert impl.sort_versions(["v2.0.0", "1.10.0"]) == ["1.10.0", "v2.0.0"]


def test_input_is_not_mutated():
    given = ["1.1.0", "1.0.0"]
    impl.sort_versions(given)
    assert given == ["1.1.0", "1.0.0"]


def test_empty_input():
    assert impl.sort_versions([]) == []


@pytest.mark.parametrize(
    "bad", ["1.0", "1.01.0", "1.0.0-01", "1.0.0-", "1.0.0-a..b", "banana", ""]
)
def test_invalid_tags_raise_value_error_naming_the_tag(bad):
    with pytest.raises(ValueError) as excinfo:
        impl.sort_versions(["1.0.0", bad])
    assert bad in str(excinfo.value)
