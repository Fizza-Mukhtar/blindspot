import pytest

import impl
from impl import resolve_range, UnsatisfiableRange


LENGTH = 1000


def test_exception_hierarchy():
    assert issubclass(UnsatisfiableRange, Exception)
    assert not issubclass(UnsatisfiableRange, ValueError)


def test_simple_first_last():
    assert resolve_range("bytes=0-499", LENGTH) == [(0, 499)]
    assert resolve_range("bytes=500-999", LENGTH) == [(500, 999)]


def test_open_ended_first_only():
    assert resolve_range("bytes=500-", LENGTH) == [(500, 999)]


def test_suffix_range():
    assert resolve_range("bytes=-500", LENGTH) == [(500, 999)]


def test_suffix_longer_than_object_returns_whole():
    assert resolve_range("bytes=-5000", LENGTH) == [(0, 999)]


def test_last_byte_pos_clamped_when_past_end():
    assert resolve_range("bytes=0-9999", LENGTH) == [(0, 999)]


def test_zero_suffix_is_unsatisfiable():
    with pytest.raises(UnsatisfiableRange):
        resolve_range("bytes=-0", LENGTH)


def test_first_at_or_past_length_is_unsatisfiable():
    with pytest.raises(UnsatisfiableRange):
        resolve_range("bytes=1000-", LENGTH)
    with pytest.raises(UnsatisfiableRange):
        resolve_range("bytes=5000-6000", LENGTH)


def test_last_less_than_first_is_malformed_and_ignored():
    assert resolve_range("bytes=2-1", LENGTH) == [(0, 999)]
    assert resolve_range("bytes=0-1,5-3", LENGTH) == [(0, 999)]


def test_multiple_ranges_preserve_order():
    assert resolve_range("bytes=0-0,-1", LENGTH) == [(0, 0), (999, 999)]


def test_mixed_satisfiable_and_unsatisfiable_drops_bad_ones():
    result = resolve_range("bytes=100-199,5000-5100,0-0", LENGTH)
    assert result == [(100, 199), (0, 0)]


def test_empty_list_elements_are_skipped():
    assert resolve_range("bytes=0-0, ,-1", LENGTH) == [(0, 0), (999, 999)]


def test_case_insensitive_unit_and_leading_zeroes():
    assert resolve_range("Bytes=0-0", LENGTH) == [(0, 0)]
    assert resolve_range("bytes=007-009", LENGTH) == [(7, 9)]


def test_surrounding_whitespace_on_header_is_ignored():
    assert resolve_range(" \tbytes=0-499\t ", LENGTH) == [(0, 499)]


@pytest.mark.parametrize(
    "header",
    [
        "items=0-5",     # unrecognized unit
        "bytes=abc",     # garbage digits
        "bytes",         # missing '='
        "bytes=",         # empty range set
        "bytes=-",        # bare '-'
        "bytes = 0-1",   # whitespace around '='
        "bytes=0 - 1",   # whitespace inside spec
    ],
)
def test_malformed_headers_are_ignored_and_serve_whole(header):
    assert resolve_range(header, LENGTH) == [(0, LENGTH - 1)]


def test_zero_length_representation_always_unsatisfiable():
    with pytest.raises(UnsatisfiableRange):
        resolve_range("bytes=0-499", 0)
    with pytest.raises(UnsatisfiableRange):
        resolve_range("garbage that would normally be ignored", 0)


def test_invalid_argument_types_raise_value_error():
    with pytest.raises(ValueError):
        resolve_range(123, LENGTH)
    with pytest.raises(ValueError):
        resolve_range("bytes=0-1", "1000")
    with pytest.raises(ValueError):
        resolve_range("bytes=0-1", -1)
    with pytest.raises(ValueError):
        resolve_range("bytes=0-1", True and -5)


def test_single_byte_range_is_inclusive_length_one():
    assert resolve_range("bytes=0-0", LENGTH) == [(0, 0)]
