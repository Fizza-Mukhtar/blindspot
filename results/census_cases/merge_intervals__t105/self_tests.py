import pytest
import impl


def test_empty_input():
    """Empty input returns empty output."""
    result = impl.merge_bookings([])
    assert result == []


def test_single_interval():
    """Single interval is returned unchanged."""
    result = impl.merge_bookings([(60, 120)])
    assert result == [(60, 120)]


def test_multiple_non_overlapping():
    """Non-overlapping intervals remain separate and sorted."""
    result = impl.merge_bookings([(180, 240), (60, 120)])
    assert result == [(60, 120), (180, 240)]


def test_overlapping_intervals():
    """Overlapping intervals are merged."""
    result = impl.merge_bookings([(60, 180), (120, 240)])
    assert result == [(60, 240)]


def test_adjacent_intervals_merge():
    """Adjacent intervals [60, 120) and [120, 180) merge."""
    result = impl.merge_bookings([(60, 120), (120, 180)])
    assert result == [(60, 180)]


def test_gap_between_intervals():
    """Intervals with a gap [60, 120) and [121, 180) stay separate."""
    result = impl.merge_bookings([(60, 120), (121, 180)])
    assert result == [(60, 120), (121, 180)]


def test_zero_width_intervals_dropped():
    """Zero-width intervals (cancellations) are dropped silently."""
    result = impl.merge_bookings([(0, 60), (90, 90), (120, 180)])
    assert result == [(0, 60), (120, 180)]


def test_all_zero_width_returns_empty():
    """If all intervals are zero-width, return empty list."""
    result = impl.merge_bookings([(60, 60), (90, 90)])
    assert result == []


def test_duplicate_intervals():
    """Exact duplicates are merged into single interval."""
    result = impl.merge_bookings([(60, 120), (60, 120)])
    assert result == [(60, 120)]


def test_nested_intervals():
    """Nested intervals are merged."""
    result = impl.merge_bookings([(60, 300), (120, 180)])
    assert result == [(60, 300)]


def test_ticket_example():
    """Complex example from ticket is correctly merged."""
    result = impl.merge_bookings(
        [(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)]
    )
    assert result == [(480, 630), (690, 720)]


def test_negative_minutes():
    """Negative minutes are handled correctly."""
    result = impl.merge_bookings([(-60, 0), (0, 60)])
    assert result == [(-60, 60)]


def test_list_and_tuple_input():
    """Both lists and tuples are accepted as intervals."""
    result = impl.merge_bookings([[60, 120], (180, 240)])
    assert result == [(60, 120), (180, 240)]


def test_output_is_list_of_tuples():
    """Output is always tuples, even if input contains lists."""
    result = impl.merge_bookings([[60, 120]])
    assert isinstance(result, list)
    assert all(isinstance(item, tuple) for item in result)


def test_input_not_mutated():
    """The input list is not mutated by the function."""
    original = [(60, 120), (180, 240)]
    original_copy = original.copy()
    impl.merge_bookings(original)
    assert original == original_copy


def test_error_start_greater_than_end():
    """ValueError raised when start > end, message contains (start, end)."""
    with pytest.raises(ValueError) as exc_info:
        impl.merge_bookings([(120, 60)])
    error_msg = str(exc_info.value)
    assert "(120, 60)" in error_msg


def test_error_not_tuple_or_list():
    """ValueError raised when entry is not a tuple or list."""
    with pytest.raises(ValueError):
        impl.merge_bookings([60])


def test_error_wrong_length():
    """ValueError raised when entry doesn't have exactly 2 elements."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(60, 120, 180)])


def test_error_non_integer_start():
    """ValueError raised when start is not an integer."""
    with pytest.raises(ValueError):
        impl.merge_bookings([("60", 120)])


def test_error_non_integer_end():
    """ValueError raised when end is not an integer."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(60, "120")])
