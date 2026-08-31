"""Tests for releng.tagsort.sort_versions (RELENG-412)."""

import pytest

import impl


def test_empty_list_returns_empty_list():
    assert impl.sort_versions([]) == []


def test_does_not_mutate_input():
    original = ["v2.0.0", "v1.0.0", "v1.5.0"]
    snapshot = list(original)
    impl.sort_versions(original)
    assert original == snapshot


def test_returns_new_list_object():
    tags = ["1.0.0", "2.0.0"]
    result = impl.sort_versions(tags)
    assert result is not tags


def test_numeric_major_minor_patch_ordering():
    tags = ["1.0.10", "1.0.9", "2.0.0", "1.9.0", "1.10.0", "0.1.0"]
    assert impl.sort_versions(tags) == [
        "0.1.0",
        "1.0.9",
        "1.0.10",
        "1.9.0",
        "1.10.0",
        "2.0.0",
    ]


def test_prerelease_has_lower_precedence_than_release():
    tags = ["1.0.0", "1.0.0-rc.1"]
    assert impl.sort_versions(tags) == ["1.0.0-rc.1", "1.0.0"]


def test_spec_reference_ordering_example():
    # Shuffled input; expected output is the canonical semver.org example order.
    tags = [
        "1.0.0-beta.11",
        "1.0.0",
        "1.0.0-alpha",
        "1.0.0-rc.1",
        "1.0.0-alpha.1",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-alpha.beta",
    ]
    assert impl.sort_versions(tags) == [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]


def test_numeric_prerelease_identifiers_compared_numerically():
    tags = ["v1.0.0-rc.10", "v1.0.0-rc.2", "v1.0.0-rc.9"]
    assert impl.sort_versions(tags) == [
        "v1.0.0-rc.2",
        "v1.0.0-rc.9",
        "v1.0.0-rc.10",
    ]


def test_alphanumeric_prerelease_identifiers_compared_lexically():
    tags = ["1.0.0-rc.b", "1.0.0-rc.a", "1.0.0-rc.aa"]
    assert impl.sort_versions(tags) == [
        "1.0.0-rc.a",
        "1.0.0-rc.aa",
        "1.0.0-rc.b",
    ]


def test_numeric_identifier_lower_precedence_than_alphanumeric():
    # At the same identifier position, a purely numeric identifier always
    # sorts below a non-numeric one, regardless of the literal characters.
    tags = ["1.0.0-rc.x", "1.0.0-rc.9"]
    assert impl.sort_versions(tags) == ["1.0.0-rc.9", "1.0.0-rc.x"]


def test_more_identifiers_have_higher_precedence_on_common_prefix():
    tags = ["1.0.0-alpha.1", "1.0.0-alpha"]
    assert impl.sort_versions(tags) == ["1.0.0-alpha", "1.0.0-alpha.1"]


def test_build_metadata_ignored_for_precedence():
    tags = ["1.0.0+build.99", "1.0.0+build.1"]
    result = impl.sort_versions(tags)
    # Equal precedence -> original relative order preserved (stability),
    # and the exact original strings (with their build metadata) are kept.
    assert result == ["1.0.0+build.99", "1.0.0+build.1"]


def test_stable_sort_for_equal_precedence_mixed_with_others():
    tags = ["1.0.0+a", "0.9.0", "1.0.0+b", "0.9.0+later"]
    # 0.9.0 and 0.9.0+later have equal precedence and keep their relative
    # order; likewise 1.0.0+a before 1.0.0+b.
    assert impl.sort_versions(tags) == [
        "0.9.0",
        "0.9.0+later",
        "1.0.0+a",
        "1.0.0+b",
    ]


def test_leading_v_is_decorative_and_preserved_in_output():
    tags = ["v1.0.0", "0.9.12+exp.sha.5114f85", "1.0.0-alpha.1"]
    result = impl.sort_versions(tags)
    assert result == ["0.9.12+exp.sha.5114f85", "1.0.0-alpha.1", "v1.0.0"]
    # exact original strings, v included, come back untouched
    assert "v1.0.0" in result


def test_invalid_format_raises_value_error_with_tag_in_message():
    with pytest.raises(ValueError) as excinfo:
        impl.sort_versions(["1.0", "1.0.0"])
    assert "1.0" in str(excinfo.value)


@pytest.mark.parametrize(
    "bad_tag",
    ["1.01.0", "01.0.0", "1.0.01"],
)
def test_leading_zero_in_numeric_part_is_invalid(bad_tag):
    with pytest.raises(ValueError) as excinfo:
        impl.sort_versions([bad_tag])
    assert bad_tag in str(excinfo.value)


def test_leading_zero_in_numeric_prerelease_identifier_is_invalid():
    with pytest.raises(ValueError) as excinfo:
        impl.sort_versions(["1.0.0-rc.01"])
    assert "1.0.0-rc.01" in str(excinfo.value)


@pytest.mark.parametrize(
    "bad_tag",
    ["1.0.0-", "1.0.0-a..b", "1.0.0-a."],
)
def test_empty_prerelease_identifier_is_invalid(bad_tag):
    with pytest.raises(ValueError) as excinfo:
        impl.sort_versions([bad_tag])
    assert bad_tag in str(excinfo.value)


def test_single_element_list_returned_unchanged():
    assert impl.sort_versions(["v1.2.3"]) == ["v1.2.3"]
