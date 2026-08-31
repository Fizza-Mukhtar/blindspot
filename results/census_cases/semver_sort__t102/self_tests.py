import impl
import pytest


def test_empty_list():
    """Empty input yields empty output."""
    assert impl.sort_versions([]) == []


def test_single_element():
    """Single element is returned as-is."""
    assert impl.sort_versions(["1.0.0"]) == ["1.0.0"]


def test_basic_sorting():
    """Versions sort in correct order."""
    tags = ["2.0.0", "1.0.0", "1.1.0", "1.0.1"]
    expected = ["1.0.0", "1.0.1", "1.1.0", "2.0.0"]
    assert impl.sort_versions(tags) == expected


def test_leading_v_preserved():
    """Leading 'v' doesn't affect sorting and is preserved in output."""
    tags = ["v2.0.0", "1.0.0", "v1.1.0", "1.0.1"]
    expected = ["1.0.0", "1.0.1", "v1.1.0", "v2.0.0"]
    assert impl.sort_versions(tags) == expected


def test_prerelease_before_release():
    """Pre-release versions sort before release versions."""
    tags = ["1.0.0", "1.0.0-alpha", "1.0.0-beta", "1.0.0-rc.1"]
    expected = ["1.0.0-alpha", "1.0.0-beta", "1.0.0-rc.1", "1.0.0"]
    assert impl.sort_versions(tags) == expected


def test_prerelease_numeric_before_alphanumeric():
    """Numeric pre-release identifiers sort before alphanumeric."""
    tags = ["1.0.0-1", "1.0.0-alpha"]
    expected = ["1.0.0-1", "1.0.0-alpha"]
    assert impl.sort_versions(tags) == expected


def test_prerelease_numeric_ordering():
    """Numeric pre-release identifiers compared numerically (the original bug)."""
    tags = ["1.0.0-rc.10", "1.0.0-rc.2", "1.0.0-rc.1"]
    expected = ["1.0.0-rc.1", "1.0.0-rc.2", "1.0.0-rc.10"]
    assert impl.sort_versions(tags) == expected


def test_prerelease_alphanumeric_ordering():
    """Alphanumeric pre-release identifiers compared lexically."""
    tags = ["1.0.0-beta", "1.0.0-alpha", "1.0.0-alpha.1"]
    expected = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-beta"]
    assert impl.sort_versions(tags) == expected


def test_build_metadata_ignored_in_sort():
    """Build metadata doesn't affect precedence."""
    tags = ["1.0.0+build.99", "1.0.0+build.1", "1.0.0"]
    expected = ["1.0.0+build.99", "1.0.0+build.1", "1.0.0"]
    assert impl.sort_versions(tags) == expected


def test_stable_sort_preserves_order():
    """Equal precedence versions maintain input order."""
    tags = ["1.0.0+a", "1.0.0+b", "1.0.0+c"]
    assert impl.sort_versions(tags) == tags


def test_complex_sort_order():
    """Complex mix of versions with v prefix, pre-release, build metadata."""
    tags = [
        "v2.0.0-beta",
        "1.0.0-alpha.1",
        "1.0.0-alpha",
        "2.0.0",
        "1.0.0",
        "1.0.1-rc.1",
        "1.0.1",
        "v1.0.0-alpha.beta",
    ]
    expected = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "v1.0.0-alpha.beta",
        "1.0.0",
        "1.0.1-rc.1",
        "1.0.1",
        "v2.0.0-beta",
        "2.0.0",
    ]
    assert impl.sort_versions(tags) == expected


def test_no_mutation():
    """Input list is not mutated."""
    original = ["2.0.0", "1.0.0"]
    tags = original.copy()
    impl.sort_versions(tags)
    assert tags == original


@pytest.mark.parametrize("tag", ["1.0", "1.0.0.1"])
def test_error_wrong_version_parts_count(tag):
    """Tags without exactly 3 core version parts raise ValueError."""
    with pytest.raises(ValueError):
        impl.sort_versions([tag])


@pytest.mark.parametrize("tag", ["01.0.0", "1.01.0", "1.0.01"])
def test_error_leading_zero_on_version(tag):
    """Core version numbers with leading zeros raise ValueError."""
    with pytest.raises(ValueError):
        impl.sort_versions([tag])


@pytest.mark.parametrize("tag", ["1.0.0-01", "1.0.0-", "1.0.0-alpha..beta"])
def test_error_invalid_prerelease(tag):
    """Invalid pre-release formats raise ValueError."""
    with pytest.raises(ValueError):
        impl.sort_versions([tag])


def test_error_non_numeric_core_version():
    """Core version parts must be numeric."""
    with pytest.raises(ValueError):
        impl.sort_versions(["1.a.0"])


def test_valid_zero_versions():
    """Core versions with 0 are valid (0 is not a leading zero)."""
    tags = ["0.0.0", "0.0.1", "0.1.0", "1.0.0"]
    expected = ["0.0.0", "0.0.1", "0.1.0", "1.0.0"]
    assert impl.sort_versions(tags) == expected


def test_valid_zero_prerelease():
    """Numeric pre-release identifier of 0 is valid."""
    tags = ["1.0.0-0", "1.0.0-1"]
    expected = ["1.0.0-0", "1.0.0-1"]
    assert impl.sort_versions(tags) == expected
