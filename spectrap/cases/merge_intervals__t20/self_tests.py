import impl
import pytest


def test_empty_input():
    """Empty input returns empty list."""
    assert impl.merge_bookings([]) == []


def test_single_interval():
    """Single interval is returned as-is."""
    assert impl.merge_bookings([(540, 600)]) == [(540, 600)]


def test_multiple_non_overlapping():
    """Non-overlapping intervals stay separate."""
    result = impl.merge_bookings([(100, 200), (300, 400), (500, 600)])
    assert result == [(100, 200), (300, 400), (500, 600)]


def test_overlapping_and_adjacent_intervals():
    """Overlapping and adjacent intervals merge correctly."""
    # Overlapping
    assert impl.merge_bookings([(100, 200), (150, 250)]) == [(100, 250)]
    # Adjacent with no gap (boundary at 120)
    assert impl.merge_bookings([(60, 120), (120, 180)]) == [(60, 180)]
    # Adjacent with gap (minute 120 is free)
    assert impl.merge_bookings([(60, 120), (121, 180)]) == [(60, 120), (121, 180)]


def test_unsorted_input():
    """Unsorted input is sorted and merged correctly."""
    result = impl.merge_bookings([(700, 720), (100, 200), (400, 500)])
    assert result == [(100, 200), (400, 500), (700, 720)]


def test_ticket_example():
    """Test the exact example from the ticket."""
    result = impl.merge_bookings(
        [(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)]
    )
    assert result == [(480, 630), (690, 720)]


def test_duplicates_and_nested():
    """Duplicate and nested intervals merge correctly."""
    # Duplicates
    assert impl.merge_bookings([(60, 120), (60, 120)]) == [(60, 120)]
    # Nested intervals
    assert impl.merge_bookings([(60, 300), (120, 180)]) == [(60, 300)]


def test_zero_width_intervals():
    """Zero-width intervals (start == end) are silently dropped."""
    assert impl.merge_bookings([(0, 60), (90, 90), (120, 180)]) == [(0, 60), (120, 180)]
    assert impl.merge_bookings([(100, 100), (200, 200)]) == []


def test_negative_minutes():
    """Negative minutes (night shift) and crossing midnight are handled."""
    assert impl.merge_bookings([(-60, 0), (0, 60)]) == [(-60, 60)]
    assert impl.merge_bookings([(-120, -60), (-60, 60)]) == [(-120, 60)]


def test_list_input():
    """List entries are accepted and output is always tuples."""
    result = impl.merge_bookings([[60, 120], [120, 180]])
    assert result == [(60, 180)]
    assert all(isinstance(interval, tuple) for interval in result)


def test_input_not_mutated():
    """Input list and entries are not mutated."""
    intervals = [(540, 600), (600, 630)]
    original = intervals.copy()
    impl.merge_bookings(intervals)
    assert intervals == original


def test_start_greater_than_end_error():
    """ValueError raised when start > end with pair in error message."""
    with pytest.raises(ValueError) as exc_info:
        impl.merge_bookings([(120, 60)])
    assert "(120, 60)" in str(exc_info.value)
    
    with pytest.raises(ValueError) as exc_info:
        impl.merge_bookings([[999, 500]])
    assert "(999, 500)" in str(exc_info.value)


def test_invalid_entry_type_error():
    """ValueError raised for non-tuple/non-list entries."""
    with pytest.raises(ValueError):
        impl.merge_bookings([{0: 60, 1: 120}])
    
    with pytest.raises(ValueError):
        impl.merge_bookings(["60,120"])


def test_wrong_element_count_error():
    """ValueError raised for entries with wrong number of elements."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(60, 120, 180)])
    
    with pytest.raises(ValueError):
        impl.merge_bookings([(60,)])
    
    with pytest.raises(ValueError):
        impl.merge_bookings([tuple()])


def test_non_integer_elements_error():
    """ValueError raised when elements are not integers."""
    with pytest.raises(ValueError):
        impl.merge_bookings([(60.5, 120)])
    
    with pytest.raises(ValueError):
        impl.merge_bookings([(60, "120")])
    
    with pytest.raises(ValueError):
        impl.merge_bookings([(None, 120)])


def test_complex_merge_scenario():
    """Complex scenario with overlaps, gaps, duplicates, and zero-width."""
    result = impl.merge_bookings([
        (0, 10),
        (5, 15),
        (5, 15),  # duplicate
        (20, 30),
        (25, 35),
        (40, 50),
        (0, 0),   # zero-width, dropped
    ])
    assert result == [(0, 15), (20, 35), (40, 50)]
