import pytest
import impl


def test_example_from_ticket():
    """Test the exact example from the ticket."""
    result = impl.merge_bookings([(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)])
    assert result == [(480, 630), (690, 720)]


def test_empty_input():
    """Empty input returns empty list."""
    assert impl.merge_bookings([]) == []


def test_single_interval():
    """Single interval is returned as-is."""
    assert impl.merge_bookings([(100, 200)]) == [(100, 200)]


def test_non_overlapping_intervals():
    """Non-overlapping intervals stay separate."""
    assert impl.merge_bookings([(0, 100), (200, 300)]) == [(0, 100), (200, 300)]


def test_adjacent_intervals_merge():
    """Adjacent intervals [60, 120) and [120, 180) merge to [60, 180)."""
    result = impl.merge_bookings([(60, 120), (120, 180)])
    assert result == [(60, 180)]


def test_overlapping_intervals_merge():
    """Overlapping intervals merge."""
    result = impl.merge_bookings([(60, 150), (100, 200)])
    assert result == [(60, 200)]


def test_nested_interval():
    """Nested interval is absorbed by outer interval."""
    result = impl.merge_bookings([(60, 300), (120, 180)])
    assert result == [(60, 300)]


def test_unsorted_input():
    """Unsorted input is correctly merged and sorted in output."""
    result = impl.merge_bookings([(300, 400), (100, 200), (250, 350)])
    assert result == [(100, 200), (250, 400)]


def test_exact_duplicates():
    """Exact duplicates are merged to single interval."""
    result = impl.merge_bookings([(60, 120), (60, 120)])
    assert result == [(60, 120)]


def test_zero_width_dropped():
    """Zero-width intervals (cancellations) are dropped silently."""
    result = impl.merge_bookings([(0, 60), (90, 90), (120, 180)])
    assert result == [(0, 60), (120, 180)]


def test_all_zero_width():
    """All zero-width intervals returns empty list."""
    assert impl.merge_bookings([(0, 0), (50, 50), (100, 100)]) == []


def test_negative_minutes():
    """Negative minutes (night shift) are handled correctly."""
    result = impl.merge_bookings([(-60, 0), (0, 60)])
    assert result == [(-60, 60)]


def test_start_greater_than_end_raises_error():
    """start > end raises ValueError with (start, end) in message."""
    with pytest.raises(ValueError, match=r"\(120, 60\)"):
        impl.merge_bookings([(120, 60)])


def test_wrong_length_entry_raises_error():
    """Entry with wrong number of elements raises ValueError."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(100,)])


def test_non_integer_values_raise_error():
    """Non-integer values raise ValueError."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(100.5, 200)])


def test_list_entries_accepted():
    """List entries are accepted (not just tuples)."""
    result = impl.merge_bookings([[100, 200], [250, 300]])
    assert result == [(100, 200), (250, 300)]


def test_output_always_tuples():
    """Output entries are always tuples, even if input has lists."""
    result = impl.merge_bookings([[100, 200]])
    assert isinstance(result[0], tuple)
    assert result == [(100, 200)]


def test_input_not_mutated():
    """Input list is not mutated by the function."""
    original = [(300, 400), (100, 200)]
    copy = list(original)
    impl.merge_bookings(original)
    assert original == copy


def test_gap_between_intervals():
    """Intervals with a gap (one free minute) stay separate: [60,120) and [121,180)."""
    result = impl.merge_bookings([(60, 120), (121, 180)])
    assert result == [(60, 120), (121, 180)]
