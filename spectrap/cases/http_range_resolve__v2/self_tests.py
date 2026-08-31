import pytest

import impl
from impl import UnsatisfiableRange, resolve_range


def test_single_range_first_last():
    assert resolve_range("bytes=0-499", 1000) == [(0, 499)]


def test_single_range_second_half():
    assert resolve_range("bytes=500-999", 1000) == [(500, 999)]


def test_open_ended_range_matches_explicit_range():
    assert resolve_range("bytes=500-", 1000) == [(500, 999)]


def test_suffix_range_matches_explicit_range():
    assert resolve_range("bytes=-500", 1000) == [(500, 999)]


def test_suffix_longer_than_length_returns_whole_object():
    assert resolve_range("bytes=-5000", 1000) == [(0, 999)]


def test_last_byte_pos_clamped_to_length_minus_one():
    assert resolve_range("bytes=0-9999", 1000) == [(0, 999)]


def test_zero_length_suffix_is_unsatisfiable():
    with pytest.raises(UnsatisfiableRange):
        resolve_range("bytes=-0", 1000)


def test_first_byte_pos_at_or_beyond_length_is_unsatisfiable():
    with pytest.raises(UnsatisfiableRange):
        resolve_range("bytes=1000-", 1000)


def test_last_less_than_first_is_malformed_and_ignored():
    # A malformed spec poisons the whole header; the whole object is served.
    assert resolve_range("bytes=2-1", 1000) == [(0, 999)]


def test_one_bad_element_poisons_the_whole_header():
    assert resolve_range("bytes=0-1,5-3", 1000) == [(0, 999)]


def test_worked_example_first_and_last_byte_in_order():
    assert resolve_range("bytes=0-0,-1", 1000) == [(0, 0), (999, 999)]


def test_unsatisfiable_specs_dropped_but_order_preserved():
    result = resolve_range("bytes=100-199,5000-5100,0-0", 1000)
    assert result == [(100, 199), (0, 0)]


def test_all_unsatisfiable_specs_raises():
    with pytest.raises(UnsatisfiableRange):
        resolve_range("bytes=5000-6000,7000-", 1000)


def test_unit_token_is_case_insensitive():
    assert resolve_range("Bytes=0-0", 1000) == [(0, 0)]


def test_leading_zeroes_carry_no_meaning():
    assert resolve_range("bytes=007-009", 1000) == [(7, 9)]


def test_whitespace_around_header_and_elements_is_ignored():
    assert resolve_range(" \tbytes=0-0, -1\t ", 1000) == [(0, 0), (999, 999)]


def test_empty_list_elements_are_skipped():
    assert resolve_range("bytes=0-0, ,-1", 1000) == [(0, 0), (999, 999)]


def test_duplicate_and_overlapping_ranges_are_not_merged():
    assert resolve_range("bytes=0-0,0-0", 1000) == [(0, 0), (0, 0)]


@pytest.mark.parametrize(
    "header",
    [
        "items=0-5",       # unrecognised unit
        "bytes=abc",       # garbage where digits belong
        "bytes=",          # empty range set
        "bytes",           # missing '='
        "bytes=-",         # bare '-'
        "bytes = 0-1",     # whitespace around '='
        "bytes=0 - 1",     # whitespace inside spec
    ],
)
def test_malformed_headers_return_whole_representation(header):
    assert resolve_range(header, 1000) == [(0, 999)]


def test_zero_length_always_raises_even_for_well_formed_header():
    with pytest.raises(UnsatisfiableRange):
        resolve_range("bytes=0-0", 0)


def test_zero_length_raises_even_for_malformed_header():
    # No whole object to fall back to when length is 0.
    with pytest.raises(UnsatisfiableRange):
        resolve_range("items=0-5", 0)


@pytest.mark.parametrize(
    "header, length",
    [
        (None, 1000),
        (b"bytes=0-1", 1000),
        ("bytes=0-1", "1000"),
        ("bytes=0-1", 1.5),
        ("bytes=0-1", -1),
    ],
)
def test_invalid_arguments_raise_value_error(header, length):
    with pytest.raises(ValueError):
        resolve_range(header, length)


def test_unsatisfiable_range_is_not_a_value_error():
    assert issubclass(UnsatisfiableRange, Exception)
    assert not issubclass(UnsatisfiableRange, ValueError)
