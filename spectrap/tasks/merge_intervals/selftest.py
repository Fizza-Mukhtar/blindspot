"""Authoritative examples for SCHED-207.

Every assertion here is traceable either to the half-open interval convention
cited by the ticket or to an explicit sentence of SPEC.md -- never merely to
what the reference implementation happens to do.  ``make verify-corpus`` runs
this against ``reference.py`` in CI, which is what lets the README claim that
ground-truth labels are verified by construction rather than by inspection.

Source: E. W. Dijkstra, EWD 831, "Why numbering should start at zero",
https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD831.html
"""

import pytest

import impl


def test_touching_bookings_form_one_block():
    """Convention consequence 1: '[60, 120) and [120, 180) ... must come back as
    the single block [60, 180)'."""
    assert impl.merge_bookings([(60, 120), (120, 180)]) == [(60, 180)]


def test_one_free_minute_keeps_the_blocks_apart():
    """Convention consequence 1: '[60, 120) and [121, 180) stay separate:
    minute 120 is free'."""
    assert impl.merge_bookings([(60, 120), (121, 180)]) == [(60, 120), (121, 180)]


def test_adjacency_chain_collapses_completely():
    """Convention consequence 1, applied transitively: a run of end-to-start
    bookings describes one continuous busy stretch."""
    given = [(0, 60), (60, 120), (120, 180), (180, 240)]
    assert impl.merge_bookings(given) == [(0, 240)]


def test_cancellation_does_not_bridge_two_separate_blocks():
    """Convention consequence 2, quoted verbatim: 'Given [(0, 60), (90, 90),
    (120, 180)] the answer is [(0, 60), (120, 180)]'."""
    assert impl.merge_bookings([(0, 60), (90, 90), (120, 180)]) == [
        (0, 60),
        (120, 180),
    ]


def test_zero_length_entry_never_appears_in_the_output():
    """Convention consequence 2: 'It must never appear in the output.'"""
    result = impl.merge_bookings([(0, 60), (90, 90), (615, 615), (120, 180)])
    assert all(start < end for start, end in result)
    assert (90, 90) not in result and (615, 615) not in result


def test_cancellation_touching_a_block_is_still_dropped():
    """Convention consequence 2: a zero-length entry occupies no time, so it can
    neither extend nor punctuate the block it abuts."""
    assert impl.merge_bookings([(0, 60), (60, 60), (120, 180)]) == [
        (0, 60),
        (120, 180),
    ]


def test_all_cancellations_yield_the_empty_list():
    """Convention consequence 2: 'If every entry is zero-length, the result is
    the empty list.'"""
    assert impl.merge_bookings([(0, 0), (615, 615), (-30, -30)]) == []


def test_zero_length_is_not_an_error():
    """Errors: 'Note that start == end is not an error.'"""
    assert impl.merge_bookings([(615, 615)]) == []


def test_unsorted_input_is_sorted_ascending_by_start():
    """Rules for the input: 'It may be in any order.'  Rules for the result:
    'Sorted ascending by start.'"""
    assert impl.merge_bookings([(300, 360), (60, 120), (120, 180)]) == [
        (60, 180),
        (300, 360),
    ]


def test_exact_duplicates_collapse():
    """Rules for the input: '[(60, 120), (60, 120)] is one busy block'."""
    assert impl.merge_bookings([(60, 120), (60, 120)]) == [(60, 120)]


def test_nested_booking_is_absorbed():
    """Rules for the input: '[(60, 300), (120, 180)] is [(60, 300)]'."""
    assert impl.merge_bookings([(60, 300), (120, 180)]) == [(60, 300)]
    assert impl.merge_bookings([(120, 180), (60, 300)]) == [(60, 300)]


def test_negative_minutes_are_accepted_and_merge_normally():
    """Rules for the input: '[(-60, 0), (0, 60)] merges to [(-60, 60)]'."""
    assert impl.merge_bookings([(-60, 0), (0, 60)]) == [(-60, 60)]


def test_negative_cancellation_is_dropped_like_any_other():
    """Convention consequence 2 combined with 'Minute values may be negative'."""
    assert impl.merge_bookings([(-120, -60), (-60, -60), (-30, 0)]) == [
        (-120, -60),
        (-30, 0),
    ]


def test_worked_example_from_the_ticket():
    """The SPEC's worked example, verbatim."""
    given = [(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)]
    assert impl.merge_bookings(given) == [(480, 630), (690, 720)]


def test_empty_input_returns_empty_list():
    """Rules for the input: 'An empty input list returns an empty list.'"""
    assert impl.merge_bookings([]) == []


def test_output_entries_are_plain_int_tuples():
    """Rules for the result: 'Entries are plain tuple objects of two ints.'"""
    result = impl.merge_bookings([(60, 120), (120, 180)])
    assert isinstance(result, list)
    for block in result:
        assert type(block) is tuple
        assert len(block) == 2
        assert all(isinstance(value, int) for value in block)


def test_a_row_may_arrive_as_a_list():
    """Rules for the input: 'An entry may be a tuple or a list of exactly two
    ints. Both are accepted; the output is always tuples.'"""
    assert impl.merge_bookings([(0, 60), [60, 120]]) == [(0, 120)]


def test_input_is_not_mutated():
    """What to build: 'Do not mutate the input list or any entry in it.'"""
    given = [(300, 360), (60, 120), (120, 180)]
    snapshot = [tuple(pair) for pair in given]
    impl.merge_bookings(given)
    assert given == snapshot


@pytest.mark.parametrize("bad", [(120, 60), (0, -1), (-30, -60)])
def test_start_after_end_raises_value_error_naming_the_pair(bad):
    """Errors: 'any entry has start > end. The message must contain the
    offending pair rendered as (start, end)'."""
    with pytest.raises(ValueError) as excinfo:
        impl.merge_bookings([(0, 60), bad])
    assert f"({bad[0]}, {bad[1]})" in str(excinfo.value)


@pytest.mark.parametrize(
    "bad", [(1, 2, 3), (60,), "60", 60, (60, 120.0), (None, 60), []]
)
def test_malformed_entries_raise_value_error(bad):
    """Errors: 'any entry is not a two-element tuple or list, or either of its
    two elements is not an int.'"""
    with pytest.raises(ValueError):
        impl.merge_bookings([(0, 60), bad])
