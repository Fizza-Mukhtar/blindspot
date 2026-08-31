import pytest

import impl


def test_empty_input_returns_empty_list():
    assert impl.merge_bookings([]) == []


def test_touching_intervals_merge_into_one_block():
    result = impl.merge_bookings([(60, 120), (120, 180)])
    assert result == [(60, 180)]


def test_one_minute_gap_keeps_blocks_separate():
    result = impl.merge_bookings([(60, 120), (121, 180)])
    assert result == [(60, 120), (121, 180)]


def test_zero_length_entry_dropped_before_merge_does_not_bridge_gap():
    result = impl.merge_bookings([(0, 60), (90, 90), (120, 180)])
    assert result == [(0, 60), (120, 180)]


def test_all_zero_length_entries_return_empty_list():
    result = impl.merge_bookings([(5, 5), (10, 10), (-3, -3)])
    assert result == []


def test_exact_duplicate_intervals_collapse_to_one():
    result = impl.merge_bookings([(60, 120), (60, 120)])
    assert result == [(60, 120)]


def test_nested_interval_absorbed_by_outer():
    result = impl.merge_bookings([(60, 300), (120, 180)])
    assert result == [(60, 300)]


def test_unsorted_input_produces_sorted_output():
    result = impl.merge_bookings([(700, 720), (480, 540), (600, 630)])
    assert result == [(480, 540), (600, 630), (700, 720)]


def test_negative_minutes_merge_across_midnight():
    result = impl.merge_bookings([(-60, 0), (0, 60)])
    assert result == [(-60, 60)]


def test_list_entries_accepted_and_output_is_always_tuples():
    result = impl.merge_bookings([[10, 20], [20, 30]])
    assert result == [(10, 30)]
    for block in result:
        assert isinstance(block, tuple)


def test_worked_example_from_ticket():
    result = impl.merge_bookings(
        [(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)]
    )
    assert result == [(480, 630), (690, 720)]


def test_single_cancelled_booking_returns_empty_list():
    assert impl.merge_bookings([(615, 615)]) == []


def test_disjoint_non_touching_bookings_both_kept():
    result = impl.merge_bookings([(0, 10), (20, 30)])
    assert result == [(0, 10), (20, 30)]


def test_error_start_greater_than_end_message_contains_pair():
    with pytest.raises(ValueError) as exc_info:
        impl.merge_bookings([(120, 60)])
    assert "(120, 60)" in str(exc_info.value)


def test_error_entry_wrong_length_raises_value_error():
    with pytest.raises(ValueError):
        impl.merge_bookings([(10, 20, 30)])


def test_error_entry_non_int_element_raises_value_error():
    with pytest.raises(ValueError):
        impl.merge_bookings([(10.0, 20)])


def test_error_entry_not_tuple_or_list_raises_value_error():
    with pytest.raises(ValueError):
        impl.merge_bookings(["10-20"])


def test_does_not_mutate_input_list_or_entries():
    original_entries = [[30, 40], [10, 20]]
    snapshot = [list(e) for e in original_entries]
    impl.merge_bookings(original_entries)
    assert original_entries == snapshot
    assert all(isinstance(e, list) for e in original_entries)


def test_output_blocks_contain_plain_int_tuples_of_two():
    result = impl.merge_bookings([(1, 2), (5, 8)])
    for block in result:
        assert isinstance(block, tuple)
        assert len(block) == 2
        assert all(isinstance(v, int) for v in block)


def test_full_coverage_and_no_extra_minutes_for_scattered_bookings():
    result = impl.merge_bookings([(0, 5), (5, 10), (10, 10), (20, 25)])
    assert result == [(0, 10), (20, 25)]
