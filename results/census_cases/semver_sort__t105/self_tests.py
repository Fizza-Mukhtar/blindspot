import impl
import pytest


def test_empty_list():
    """Empty input list returns empty list."""
    assert impl.sort_versions([]) == []


def test_single_tag():
    """Single tag returns as-is."""
    assert impl.sort_versions(['v1.0.0']) == ['v1.0.0']


def test_input_not_mutated():
    """Input list is not mutated."""
    tags = ['v2.0.0', 'v1.0.0']
    original = tags.copy()
    result = impl.sort_versions(tags)
    assert tags == original
    assert result is not tags


def test_simple_version_ordering():
    """Basic semantic versioning order: major.minor.patch."""
    tags = ['v2.0.0', 'v1.1.0', 'v1.0.1', 'v1.0.0']
    assert impl.sort_versions(tags) == ['v1.0.0', 'v1.0.1', 'v1.1.0', 'v2.0.0']


def test_prerelease_lower_precedence_than_release():
    """Pre-release versions have lower precedence than release."""
    tags = ['v1.0.0', 'v1.0.0-rc.1']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0-rc.1', 'v1.0.0']


def test_numeric_prerelease_lower_than_alphanumeric():
    """Numeric pre-release identifiers have lower precedence than alphanumeric."""
    tags = ['v1.0.0-alpha', 'v1.0.0-1']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0-1', 'v1.0.0-alpha']


def test_numeric_prerelease_integer_ordering():
    """Numeric pre-release identifiers ordered as integers, not strings."""
    tags = ['v1.0.0-rc.10', 'v1.0.0-rc.2', 'v1.0.0-rc.1']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0-rc.1', 'v1.0.0-rc.2', 'v1.0.0-rc.10']


def test_shorter_prerelease_lower_than_longer():
    """Shorter pre-release identifier list has lower precedence (same prefix)."""
    tags = ['v1.0.0-alpha.1', 'v1.0.0-alpha']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0-alpha', 'v1.0.0-alpha.1']


def test_build_metadata_does_not_affect_precedence():
    """Build metadata is outside precedence; equal versions preserve input order."""
    tags = ['v1.0.0+build.99', 'v1.0.0+build.1']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0+build.99', 'v1.0.0+build.1']


def test_leading_v_is_optional():
    """Tags with and without leading 'v' are handled correctly."""
    tags = ['2.0.0', '1.0.0', '1.1.0']
    result = impl.sort_versions(tags)
    assert result == ['1.0.0', '1.1.0', '2.0.0']


def test_complex_prerelease_with_mixed_identifiers():
    """Complex pre-release identifiers mixing letters and numbers."""
    tags = ['v1.0.0-alpha', 'v1.0.0-alpha.1', 'v1.0.0-beta', 'v1.0.0']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0-alpha', 'v1.0.0-alpha.1', 'v1.0.0-beta', 'v1.0.0']


def test_stable_sort_preserves_equal_tag_order():
    """Tags with equal precedence preserve input order (stable sort)."""
    tags = ['v1.0.0', 'v1.0.0', 'v1.0.0+build.1']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0', 'v1.0.0', 'v1.0.0+build.1']


def test_zero_versions_are_valid():
    """Version 0.0.0 and variants are valid."""
    tags = ['v0.1.0', 'v0.0.1', 'v0.0.0']
    result = impl.sort_versions(tags)
    assert result == ['v0.0.0', 'v0.0.1', 'v0.1.0']


def test_leading_zero_on_major_raises_error():
    """Leading zero on major version raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['v01.0.0'])
    assert 'v01.0.0' in str(exc_info.value)


def test_leading_zero_on_numeric_prerelease_raises_error():
    """Leading zero on numeric pre-release identifier raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['v1.0.0-01'])
    assert 'v1.0.0-01' in str(exc_info.value)


def test_empty_prerelease_identifier_raises_error():
    """Empty pre-release identifier raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['v1.0.0-alpha.'])
    assert 'v1.0.0-alpha.' in str(exc_info.value)


def test_empty_build_metadata_identifier_raises_error():
    """Empty build metadata identifier raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['v1.0.0+build.'])
    assert 'v1.0.0+build.' in str(exc_info.value)


def test_missing_patch_version_raises_error():
    """Missing patch version raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['v1.0'])
    assert 'v1.0' in str(exc_info.value)


def test_invalid_characters_raise_error():
    """Invalid characters in version raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        impl.sort_versions(['v1.0.0@invalid'])
    assert 'v1.0.0@invalid' in str(exc_info.value)


def test_ticket_scenario_rc_numeric_ordering():
    """Real-world scenario from ticket: rc.2 should come before rc.10."""
    tags = ['v1.0.0-rc.10', 'v1.0.0-rc.2', 'v1.0.0']
    result = impl.sort_versions(tags)
    assert result == ['v1.0.0-rc.2', 'v1.0.0-rc.10', 'v1.0.0']
