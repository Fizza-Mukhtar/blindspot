import impl
import pytest


def test_empty_input():
    """Empty input returns empty list."""
    assert impl.merge_bookings([]) == []


def test_single_interval():
    """Single interval returns as-is."""
    assert impl.merge_bookings([(60, 120)]) == [(60, 120)]


def test_single_zero_width():
    """Single zero-width interval (cancellation) is dropped."""
    assert impl.merge_bookings([(60, 60)]) == []


def test_duplicate_intervals():
    """Duplicate intervals are merged into one."""
    assert impl.merge_bookings([(60, 120), (60, 120)]) == [(60, 120)]


def test_overlapping_intervals():
    """Overlapping intervals are merged."""
    assert impl.merge_bookings([(60, 120), (90, 150)]) == [(60, 150)]


def test_adjacent_intervals():
    """Adjacent intervals with no gap are merged."""
    assert impl.merge_bookings([(60, 120), (120, 180)]) == [(60, 180)]


def test_non_adjacent_intervals():
    """Non-adjacent intervals (with a gap) stay separate."""
    assert impl.merge_bookings([(60, 120), (121, 180)]) == [(60, 120), (121, 180)]


def test_nested_intervals():
    """Nested intervals are merged into the larger one."""
    assert impl.merge_bookings([(60, 300), (120, 180)]) == [(60, 300)]


def test_unsorted_input():
    """Unsorted input is correctly merged and sorted."""
    result = impl.merge_bookings([(700, 720), (540, 600), (600, 630)])
    assert result == [(540, 630), (700, 720)]


def test_negative_minutes():
    """Negative minutes are handled correctly."""
    assert impl.merge_bookings([(-60, 0), (0, 60)]) == [(-60, 60)]


def test_list_instead_of_tuple():
    """Lists are accepted as input and converted to tuples in output."""
    result = impl.merge_bookings([[60, 120], [120, 180]])
    assert result == [(60, 180)]
    assert all(isinstance(interval, tuple) for interval in result)


def test_complex_example_from_ticket():
    """Test the complex example from the ticket."""
    result = impl.merge_bookings([
        (540, 600), (600, 630), (630, 630),
        (700, 720), (690, 700), (480, 540)
    ])
    assert result == [(480, 630), (690, 720)]


def test_multiple_gaps():
    """Multiple separate intervals with gaps stay separate."""
    result = impl.merge_bookings([(0, 60), (120, 180), (240, 300)])
    assert result == [(0, 60), (120, 180), (240, 300)]


def test_all_zero_width_intervals():
    """All zero-width intervals return empty list."""
    result = impl.merge_bookings([(60, 60), (120, 120), (180, 180)])
    assert result == []


def test_error_start_greater_than_end():
    """ValueError raised when start > end, with pair in message."""
    with pytest.raises(ValueError) as exc_info:
        impl.merge_bookings([(120, 60)])
    assert "(120, 60)" in str(exc_info.value)


def test_error_non_integer():
    """ValueError raised when entry contains non-integer values."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(60.5, 120)])
    with pytest.raises(ValueError):
        impl.merge_bookings([(60, 120.5)])


def test_error_non_tuple_list():
    """ValueError raised when entry is not a tuple or list."""
    with pytest.raises(ValueError):
        impl.merge_bookings(["60,120"])


def test_error_wrong_number_of_elements():
    """ValueError raised when entry doesn't have exactly 2 elements."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(60, 120, 180)])
    with pytest.raises(ValueError):
        impl.merge_bookings([(60,)])


def test_boolean_not_accepted():
    """Boolean values should not be accepted as integers."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(True, 120)])


def test_zero_width_doesnt_glue():
    """Zero-width intervals don't glue separate bookings together."""
    result = impl.merge_bookings([(0, 60), (90, 90), (120, 180)])
    assert result == [(0, 60), (120, 180)]
