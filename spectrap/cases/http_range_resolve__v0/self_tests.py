import pytest

import impl


def test_worked_example_first_and_last_byte():
    assert impl.resolve_range("bytes=0-0,-1", 1000) == [(0, 0), (999, 999)]


def test_basic_ranges_all_equivalent_second_half():
    assert impl.resolve_range("bytes=0-499", 1000) == [(0, 499)]
    assert impl.resolve_range("bytes=500-999", 1000) == [(500, 999)]
    assert impl.resolve_range("bytes=500-", 1000) == [(500, 999)]
    assert impl.resolve_range("bytes=-500", 1000) == [(500, 999)]


def test_last_byte_pos_clamped_when_past_end():
    assert impl.resolve_range("bytes=0-9999", 1000) == [(0, 999)]


def test_suffix_longer_than_representation_returns_whole():
    assert impl.resolve_range("bytes=-5000", 1000) == [(0, 999)]


def test_unsatisfiable_specs_dropped_when_others_satisfiable():
    assert impl.resolve_range("bytes=100-199,5000-5100,0-0", 1000) == [
        (100, 199),
        (0, 0),
    ]


def test_all_unsatisfiable_raises_unsatisfiable_range():
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-0", 1000)
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=1000-", 1000)
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=1000-1005,-0", 1000)


def test_malformed_headers_are_ignored_and_serve_whole_object():
    assert impl.resolve_range("bytes=2-1", 1000) == [(0, 999)]
    assert impl.resolve_range("items=0-5", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=abc", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=-", 1000) == [(0, 999)]
    assert impl.resolve_range("nobyteshere", 1000) == [(0, 999)]


def test_one_bad_element_poisons_entire_header():
    assert impl.resolve_range("bytes=0-1,5-3", 1000) == [(0, 999)]


def test_disallowed_whitespace_treated_as_malformed():
    assert impl.resolve_range("bytes = 0-1", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=0 - 1", 1000) == [(0, 999)]


def test_unit_token_case_insensitive():
    assert impl.resolve_range("Bytes=0-0", 1000) == [(0, 0)]
    assert impl.resolve_range("BYTES=0-0", 5) == [(0, 0)]


def test_whitespace_around_header_and_elements_ignored():
    assert impl.resolve_range("  bytes=0-0, -1  ", 1000) == [(0, 0), (999, 999)]
    assert impl.resolve_range("\tbytes=0-0,\t-1\t", 1000) == [(0, 0), (999, 999)]


def test_empty_list_elements_are_skipped():
    assert impl.resolve_range("bytes=0-0, ,-1", 1000) == [(0, 0), (999, 999)]


def test_order_preserved_no_sort_no_dedupe():
    assert impl.resolve_range("bytes=500-999,0-499,0-499", 1000) == [
        (500, 999),
        (0, 499),
        (0, 499),
    ]


def test_leading_zeros_carry_no_meaning():
    assert impl.resolve_range("bytes=007-009", 1000) == [(7, 9)]
    assert impl.resolve_range("bytes=-007", 1000) == [(993, 999)]


def test_zero_length_always_raises_unsatisfiable_range():
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=0-0", 0)
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("this is garbage", 0)


def test_invalid_header_type_raises_value_error():
    with pytest.raises(ValueError):
        impl.resolve_range(b"bytes=0-1", 1000)


def test_invalid_length_type_or_value_raises_value_error():
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-1", 1000.0)
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-1", -1)
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-1", True)


def test_unsatisfiable_range_exception_shape():
    assert issubclass(impl.UnsatisfiableRange, Exception)
    assert not issubclass(impl.UnsatisfiableRange, ValueError)
