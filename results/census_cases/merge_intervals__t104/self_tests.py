import impl
import pytest


def test_empty_input():
    """Empty input returns empty list."""
    assert impl.merge_bookings([]) == []


def test_single_interval():
    """Single interval returned in a list."""
    assert impl.merge_bookings([(100, 200)]) == [(100, 200)]


def test_two_non_overlapping_with_gap():
    """Non-overlapping intervals with gap stay separate."""
    assert impl.merge_bookings([(60, 120), (121, 180)]) == [(60, 120), (121, 180)]


def test_two_adjacent_intervals():
    """Adjacent intervals with no gap merge."""
    assert impl.merge_bookings([(60, 120), (120, 180)]) == [(60, 180)]


def test_two_overlapping_intervals():
    """Overlapping intervals merge."""
    assert impl.merge_bookings([(60, 150), (100, 200)]) == [(60, 200)]


def test_nested_intervals():
    """Nested intervals merge into outer interval."""
    assert impl.merge_bookings([(60, 300), (120, 180)]) == [(60, 300)]


def test_complex_example_from_ticket():
    """Test the exact example from the ticket."""
    result = impl.merge_bookings([(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)])
    assert result == [(480, 630), (690, 720)]


def test_exact_duplicates():
    """Duplicate intervals merge into single interval."""
    assert impl.merge_bookings([(60, 120), (60, 120)]) == [(60, 120)]


def test_zero_width_intervals_dropped():
    """Zero-width intervals (cancellations) are silently dropped."""
    assert impl.merge_bookings([(0, 60), (90, 90), (120, 180)]) == [(0, 60), (120, 180)]


def test_all_zero_width_returns_empty():
    """All zero-width intervals returns empty list."""
    assert impl.merge_bookings([(10, 10), (20, 20)]) == []


def test_unordered_input():
    """Unordered input is sorted correctly."""
    result = impl.merge_bookings([(700, 720), (480, 540), (540, 600)])
    assert result == [(480, 600), (700, 720)]


def test_negative_minutes():
    """Negative minute values are handled correctly."""
    result = impl.merge_bookings([(-60, 0), (0, 60)])
    assert result == [(-60, 60)]


def test_list_input():
    """Intervals as lists are accepted."""
    assert impl.merge_bookings([[60, 120], [120, 180]]) == [(60, 180)]


def test_output_is_tuples():
    """Output intervals are always tuples."""
    result = impl.merge_bookings([[60, 120]])
    assert isinstance(result[0], tuple)


def test_multiple_cascading_merges():
    """Multiple overlapping intervals merge together."""
    result = impl.merge_bookings([(0, 100), (50, 150), (100, 200)])
    assert result == [(0, 200)]


def test_input_list_not_mutated():
    """Original input list is not modified."""
    original = [(60, 120), (120, 180)]
    original_copy = original.copy()
    impl.merge_bookings(original)
    assert original == original_copy


def test_error_start_greater_than_end():
    """ValueError raised when start > end with proper message format."""
    with pytest.raises(ValueError) as exc_info:
        impl.merge_bookings([(120, 60)])
    assert "(120, 60)" in str(exc_info.value)


def test_error_non_integer():
    """ValueError raised for non-integer values."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(60.5, 120)])


def test_error_wrong_structure():
    """ValueError raised for wrong tuple length."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(60, 120, 150)])
    
    with pytest.raises(ValueError):
        impl.merge_bookings([(60,)])
