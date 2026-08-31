import impl
import pytest


def test_empty_list():
    """Empty list returns empty list."""
    assert impl.sort_versions([]) == []


def test_single_version():
    """Single version returns single version."""
    assert impl.sort_versions(['1.0.0']) == ['1.0.0']


def test_basic_ordering():
    """Test basic semantic versioning ordering of major, minor, patch."""
    tags = ['2.0.0', '1.0.0', '1.1.0', '1.0.1']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0', '1.0.1', '1.1.0', '2.0.0']


def test_with_v_prefix():
    """Test that v prefix is preserved and doesn't affect ordering."""
    tags = ['v2.0.0', 'v1.0.0', '1.1.0', 'v1.0.1']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0', 'v1.0.1', '1.1.0', 'v2.0.0']


def test_prerelease_lower_precedence():
    """Pre-release versions have lower precedence than release versions."""
    tags = ['1.0.0', '1.0.0-rc.1', '1.0.0-beta', '1.0.0-alpha']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-alpha', '1.0.0-beta', '1.0.0-rc.1', '1.0.0']


def test_numeric_prerelease_identifiers():
    """Numeric pre-release identifiers are compared as integers."""
    tags = ['1.0.0-1', '1.0.0-10', '1.0.0-2', '1.0.0-alpha']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-1', '1.0.0-2', '1.0.0-10', '1.0.0-alpha']


def test_alphanumeric_prerelease_lexical():
    """Alphanumeric pre-release identifiers are compared lexically."""
    tags = ['1.0.0-beta', '1.0.0-alpha', '1.0.0-gamma']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-alpha', '1.0.0-beta', '1.0.0-gamma']


def test_multiple_prerelease_identifiers():
    """Test comparison of pre-release with multiple identifiers."""
    tags = ['1.0.0-alpha.1', '1.0.0-alpha.2', '1.0.0-alpha.1.1']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-alpha.1', '1.0.0-alpha.1.1', '1.0.0-alpha.2']


def test_build_metadata_ignored():
    """Build metadata doesn't affect ordering; stable sort preserves input order."""
    tags = ['1.0.0+build.99', '1.0.0+build.1', '1.0.0']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0+build.99', '1.0.0+build.1', '1.0.0']


def test_build_metadata_with_prerelease():
    """Build metadata with pre-release versions maintains stable sort."""
    tags = ['1.0.0-rc.1+build.1', '1.0.0-rc.1+build.2']
    result = impl.sort_versions(tags)
    assert result == tags


def test_prerelease_length_comparison():
    """Shorter pre-release has lower precedence than longer (if common parts equal)."""
    tags = ['1.0.0-rc', '1.0.0-rc.0']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0-rc', '1.0.0-rc.0']


def test_zero_versions():
    """Test with zero in version numbers."""
    tags = ['0.0.1', '0.1.0', '1.0.0', '0.0.0']
    result = impl.sort_versions(tags)
    assert result == ['0.0.0', '0.0.1', '0.1.0', '1.0.0']


def test_error_missing_patch():
    """Missing patch component raises ValueError with tag in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['1.0'])
    assert '1.0' in str(exc_info.value)


def test_error_missing_minor():
    """Missing minor component raises ValueError with tag in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['1'])
    assert '1' in str(exc_info.value)


def test_error_leading_zeros_core():
    """Leading zeros on core components raise ValueError."""
    for tag in ['01.0.0', '1.01.0', '1.0.01']:
        with pytest.raises(ValueError) as exc_info:
            impl.sort_versions([tag])
        assert tag in str(exc_info.value)


def test_error_leading_zero_prerelease():
    """Leading zero on numeric pre-release identifier raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['1.0.0-01'])
    assert '1.0.0-01' in str(exc_info.value)


def test_error_empty_prerelease_identifier():
    """Empty pre-release identifier raises ValueError."""
    for tag in ['1.0.0-rc..1', '1.0.0-rc.']:
        with pytest.raises(ValueError) as exc_info:
            impl.sort_versions([tag])
        assert tag in str(exc_info.value)


def test_error_non_numeric_core():
    """Non-numeric core component raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['1.a.0'])
    assert '1.a.0' in str(exc_info.value)


def test_stable_sort_identical_versions():
    """Stable sort maintains order for identical versions (different build metadata)."""
    tags = ['1.0.0-alpha+build.1', '1.0.0-alpha+build.2', '1.0.0-alpha']
    result = impl.sort_versions(tags)
    assert result == tags
