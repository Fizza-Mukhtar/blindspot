import pytest

import impl


def test_empty_input_returns_empty_list():
    assert impl.merge_bookings([]) == []


def test_non_overlapping_intervals_stay_separate():
    result = impl.merge_bookings([(0, 30), (60, 90)])
    assert result == [(0, 30), (60, 90)]


def test_touching_intervals_merge_into_one_block():
    # minute 120 belongs only to the second, but no free minute exists between
    result = impl.merge_bookings([(60, 120), (120, 180)])
    assert result == [(60, 180)]


def test_gap_of_one_minute_keeps_intervals_separate():
    # minute 120 is free, so these must stay apart
    result = impl.merge_bookings([(60, 120), (121, 180)])
    assert result == [(60, 120), (121, 180)]


def test_overlapping_intervals_merge():
    result = impl.merge_bookings([(0, 50), (40, 90)])
    assert result == [(0, 90)]


def test_nested_interval_is_absorbed():
    result = impl.merge_bookings([(60, 300), (120, 180)])
    assert result == [(60, 300)]


def test_exact_duplicates_collapse_to_one_block():
    result = impl.merge_bookings([(60, 120), (60, 120)])
    assert result == [(60, 120)]


def test_zero_length_bookings_are_dropped_without_bridging():
    result = impl.merge_bookings([(0, 60), (90, 90), (120, 180)])
    assert result == [(0, 60), (120, 180)]


def test_all_zero_length_bookings_yield_empty_list():
    result = impl.merge_bookings([(5, 5), (10, 10), (-3, -3)])
    assert result == []


def test_negative_minute_values_merge_across_midnight():
    result = impl.merge_bookings([(-60, 0), (0, 60)])
    assert result == [(-60, 60)]


def test_unsorted_input_with_cancellation_worked_example():
    result = impl.merge_bookings(
        [(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)]
    )
    assert result == [(480, 630), (690, 720)]


def test_list_entries_are_accepted_and_output_is_tuples():
    result = impl.merge_bookings([[0, 30], [30, 60]])
    assert result == [(0, 60)]
    for block in result:
        assert isinstance(block, tuple)
        assert all(isinstance(v, int) for v in block)


def test_input_list_and_entries_are_not_mutated():
    original_list_entry = [10, 20]
    original_tuple_entry = (30, 40)
    intervals = [original_list_entry, original_tuple_entry]
    snapshot = list(intervals)

    impl.merge_bookings(intervals)

    assert intervals == snapshot
    assert original_list_entry == [10, 20]
    assert original_tuple_entry == (30, 40)


def test_start_greater_than_end_raises_value_error_with_pair_in_message():
    with pytest.raises(ValueError) as excinfo:
        impl.merge_bookings([(120, 60)])
    assert "(120, 60)" in str(excinfo.value)


def test_start_equal_end_is_not_an_error():
    # should not raise; simply dropped
    assert impl.merge_bookings([(615, 615)]) == []


def test_wrong_length_entry_raises_value_error():
    with pytest.raises(ValueError):
        impl.merge_bookings([(1, 2, 3)])


def test_non_int_elements_raise_value_error():
    with pytest.raises(ValueError):
        impl.merge_bookings([(1.5, 10)])


def test_boolean_elements_raise_value_error():
    # bool is a subclass of int but must not be accepted as a minute value
    with pytest.raises(ValueError):
        impl.merge_bookings([(True, 10)])


def test_entry_that_is_not_tuple_or_list_raises_value_error():
    with pytest.raises(ValueError):
        impl.merge_bookings([{"start": 0, "end": 10}])


def test_result_sorted_ascending_by_start_regardless_of_input_order():
    result = impl.merge_bookings([(200, 210), (0, 10), (100, 110)])
    assert result == [(0, 10), (100, 110), (200, 210)]
    starts = [b[0] for b in result]
    assert starts == sorted(starts)
