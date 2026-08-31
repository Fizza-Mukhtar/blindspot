import impl
import pytest


# Basic sorting
def test_basic_version_sort():
    """Test basic version sorting."""
    tags = ['1.0.0', '2.0.0', '1.1.0', '1.0.1']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0', '1.0.1', '1.1.0', '2.0.0']


def test_v_prefix_handling():
    """Test that v prefix is handled and preserved."""
    tags = ['v2.0.0', 'v1.0.0', '1.1.0', 'v1.0.1']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0', 'v1.0.1', '1.1.0', 'v2.0.0']


# Prerelease versions
def test_prerelease_before_release():
    """Test that prerelease versions come before release versions."""
    tags = ['1.0.0', '1.0.0-rc.1', '1.0.0-alpha']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-alpha', '1.0.0-rc.1', '1.0.0']


def test_numeric_prerelease_identifiers():
    """Test numeric prerelease identifiers sorted numerically."""
    tags = ['1.0.0-rc.2', '1.0.0-rc.10', '1.0.0-rc.1']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-rc.1', '1.0.0-rc.2', '1.0.0-rc.10']


def test_mixed_prerelease_identifiers():
    """Test numeric identifiers have lower precedence than alphanumeric."""
    tags = ['1.0.0-1', '1.0.0-alpha', '1.0.0-1.alpha', '1.0.0-1.1']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-1', '1.0.0-1.1', '1.0.0-1.alpha', '1.0.0-alpha']


def test_complex_prerelease_sorting():
    """Test complex prerelease sorting."""
    tags = ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta', 
            '1.0.0-beta.2', '1.0.0-rc.1', '1.0.0']
    result = impl.sort_versions(tags)
    assert result == tags


# Build metadata
def test_build_metadata_ignored():
    """Test that build metadata is ignored for precedence."""
    tags = ['1.0.0+build.1', '1.0.0+build.99', '1.0.0']
    result = impl.sort_versions(tags)
    # All have same precedence, original order maintained
    assert result == tags


def test_build_metadata_with_prerelease():
    """Test build metadata with prerelease versions."""
    tags = ['1.0.0-rc.1+build.1', '1.0.0+build.1', '1.0.0-rc.1+build.2']
    result = impl.sort_versions(tags)
    # Prerelease versions come first, build metadata ignored
    assert result[0] == '1.0.0-rc.1+build.1'
    assert result[1] == '1.0.0-rc.1+build.2'
    assert result[2] == '1.0.0+build.1'


# Edge cases
def test_empty_list():
    """Test empty input list."""
    result = impl.sort_versions([])
    assert result == []


def test_single_tag():
    """Test single tag."""
    result = impl.sort_versions(['1.0.0'])
    assert result == ['1.0.0']


def test_identical_versions():
    """Test identical versions maintain original order."""
    tags = ['1.0.0', '1.0.0', '1.0.0']
    result = impl.sort_versions(tags)
    assert result == tags


def test_does_not_mutate_input():
    """Test that input list is not mutated."""
    tags = ['2.0.0', '1.0.0', '1.5.0']
    original = tags.copy()
    impl.sort_versions(tags)
    assert tags == original


# Error cases
def test_missing_version_parts():
    """Test error on missing version parts."""
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['1.0'])
    assert '1.0' in str(exc.value)
    
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['1'])
    assert '1' in str(exc.value)


def test_leading_zero_major():
    """Test error on leading zero in major version."""
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['01.0.0'])
    assert '01.0.0' in str(exc.value)


def test_leading_zero_minor():
    """Test error on leading zero in minor version."""
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['1.01.0'])
    assert '1.01.0' in str(exc.value)


def test_leading_zero_patch():
    """Test error on leading zero in patch version."""
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['1.0.01'])
    assert '1.0.01' in str(exc.value)


def test_leading_zero_prerelease():
    """Test error on leading zero in numeric prerelease identifier."""
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['1.0.0-01'])
    assert '1.0.0-01' in str(exc.value)


def test_empty_prerelease_identifier():
    """Test error on empty prerelease identifier."""
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['1.0.0-'])
    assert '1.0.0-' in str(exc.value)
    
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['1.0.0-rc..1'])
    assert '1.0.0-rc..1' in str(exc.value)


def test_non_numeric_version_number():
    """Test error on non-numeric version number."""
    with pytest.raises(ValueError) as exc:
        impl.sort_versions(['1.a.0'])
    assert '1.a.0' in str(exc.value)


# Real-world scenario
def test_real_world_version_order():
    """Test real-world versioning scenario from the ticket."""
    tags = ['v1.0.0', 'v1.0.0-rc.2', 'v1.0.0-rc.10', 'v1.0.0-beta.1', 'v2.0.0', 'v1.1.0']
    result = impl.sort_versions(tags)
    expected = ['v1.0.0-beta.1', 'v1.0.0-rc.2', 'v1.0.0-rc.10', 'v1.0.0', 'v1.1.0', 'v2.0.0']
    assert result == expected
