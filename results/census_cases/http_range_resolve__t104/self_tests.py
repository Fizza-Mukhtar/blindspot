import impl
import pytest


# Normal path
def test_single_range():
    """Single range."""
    assert impl.resolve_range("bytes=0-499", 500) == [(0, 499)]


def test_multiple_ranges():
    """Multiple ranges."""
    assert impl.resolve_range("bytes=0-99,200-299", 1000) == [(0, 99), (200, 299)]


def test_open_ended_range():
    """Range to end."""
    assert impl.resolve_range("bytes=100-", 1000) == [(100, 999)]


def test_suffix_range():
    """Last N bytes."""
    assert impl.resolve_range("bytes=-100", 1000) == [(900, 999)]


# Edge cases
def test_suffix_larger_than_length():
    """Suffix larger than length."""
    assert impl.resolve_range("bytes=-5000", 1000) == [(0, 999)]


def test_clamp_last_byte():
    """Last clamped to length-1."""
    assert impl.resolve_range("bytes=0-9999", 1000) == [(0, 999)]


def test_spaces_around_elements():
    """Spaces around elements allowed."""
    assert impl.resolve_range("bytes=0-99, 200-299", 1000) == [(0, 99), (200, 299)]


# Unsatisfiable handling
def test_unsatisfiable_ranges_dropped():
    """Unsatisfiable specs dropped."""
    assert impl.resolve_range("bytes=100-199,5000-5100,0-0", 1000) == [(100, 199), (0, 0)]


def test_all_ranges_unsatisfiable():
    """All unsatisfiable raises UnsatisfiableRange."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=5000-6000", 1000)


def test_zero_suffix_unsatisfiable():
    """Zero suffix (-0) unsatisfiable."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-0", 1000)


def test_empty_representation():
    """Empty representation raises."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=0-0", 0)


# Malformed headers return whole object
def test_wrong_unit():
    """Wrong unit."""
    assert impl.resolve_range("items=0-5", 1000) == [(0, 999)]


def test_non_digits():
    """Non-digits in numbers."""
    assert impl.resolve_range("bytes=abc-def", 1000) == [(0, 999)]


def test_invalid_range_order():
    """Last < first."""
    assert impl.resolve_range("bytes=5-3", 1000) == [(0, 999)]


def test_space_inside_spec():
    """Space inside spec."""
    assert impl.resolve_range("bytes=0 - 1", 1000) == [(0, 999)]


def test_empty_string():
    """Empty string."""
    assert impl.resolve_range("", 1000) == [(0, 999)]


# Argument validation
def test_header_not_string():
    """Header must be string."""
    with pytest.raises(ValueError):
        impl.resolve_range(123, 100)
