import impl
import pytest


def test_empty_list():
    """Empty list returns empty list"""
    result = impl.sort_versions([])
    assert result == []


def test_single_element():
    """Single element returns single element"""
    result = impl.sort_versions(['1.0.0'])
    assert result == ['1.0.0']


def test_major_version_ordering():
    """Major version ordering"""
    tags = ['2.0.0', '1.0.0', '3.0.0']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0', '2.0.0', '3.0.0']


def test_minor_version_ordering():
    """Minor version ordering"""
    tags = ['1.2.0', '1.0.0', '1.1.0']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0', '1.1.0', '1.2.0']


def test_patch_version_ordering():
    """Patch version ordering"""
    tags = ['1.0.2', '1.0.0', '1.0.1']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0', '1.0.1', '1.0.2']


def test_prerelease_lower_precedence():
    """Pre-release versions have lower precedence than release versions"""
    tags = ['1.0.0', '1.0.0-alpha']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-alpha', '1.0.0']


def test_prerelease_numeric_vs_alphanumeric():
    """Numeric pre-release identifiers come before alphanumeric per SemVer"""
    tags = ['1.0.0-1', '1.0.0-alpha']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-1', '1.0.0-alpha']


def test_prerelease_complex_ordering():
    """Complex pre-release ordering addressing the rc.2 vs rc.10 issue from ticket"""
    tags = ['1.0.0-rc.2', '1.0.0-rc.10', '1.0.0-alpha', '1.0.0']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-alpha', '1.0.0-rc.2', '1.0.0-rc.10', '1.0.0']


def test_leading_v_preserved():
    """Leading 'v' is preserved in output and doesn't affect ordering"""
    tags = ['v2.0.0', 'v1.0.0']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0', 'v2.0.0']
    assert result[0].startswith('v')


def test_mixed_v_and_no_v():
    """Mixed tags with and without leading 'v' are handled correctly"""
    tags = ['v2.0.0', '1.0.0', 'v1.5.0']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0', 'v1.5.0', 'v2.0.0']


def test_build_metadata_ignored_in_comparison():
    """Build metadata is ignored in precedence comparison"""
    tags = ['1.0.0+build.1', '1.0.0+build.99']
    result = impl.sort_versions(tags)
    assert result == tags


def test_build_metadata_preserved():
    """Build metadata is preserved in returned strings"""
    tags = ['1.0.0+exp.sha.5114f85', '0.9.12']
    result = impl.sort_versions(tags)
    assert result[1] == '1.0.0+exp.sha.5114f85'
    assert '+exp.sha.5114f85' in result[1]


def test_real_world_example_from_ticket():
    """Real-world example from RELENG-412 ticket with rc.1 vs rc.2 ordering"""
    tags = ['v1.0.0-rc.1+build.72', 'v1.0.0-rc.2', 'v1.0.0', 'v0.9.12+exp.sha.5114f85']
    result = impl.sort_versions(tags)
    expected = ['v0.9.12+exp.sha.5114f85', 'v1.0.0-rc.1+build.72', 'v1.0.0-rc.2', 'v1.0.0']
    assert result == expected


def test_stable_sort_maintains_input_order():
    """Equal precedence tags maintain input order"""
    tags = ['1.0.0+a', '1.0.0+z', '1.0.0+m']
    result = impl.sort_versions(tags)
    assert result == tags


def test_does_not_mutate_input():
    """Function does not mutate the input list"""
    original = ['2.0.0', '1.0.0', '3.0.0']
    original_copy = original.copy()
    impl.sort_versions(original)
    assert original == original_copy


def test_error_missing_patch_version():
    """ValueError raised when patch version is missing"""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['1.0'])
    assert '1.0' in str(exc_info.value)


def test_error_leading_zero_in_version():
    """ValueError raised for leading zeros in version numbers"""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['01.0.0'])
    assert '01.0.0' in str(exc_info.value)


def test_error_leading_zero_in_numeric_prerelease():
    """ValueError raised for leading zeros in numeric pre-release identifiers"""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['1.0.0-01'])
    assert '1.0.0-01' in str(exc_info.value)


def test_error_empty_prerelease_identifier():
    """ValueError raised for empty pre-release identifiers"""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['1.0.0-alpha..beta'])
    assert '1.0.0-alpha..beta' in str(exc_info.value)
