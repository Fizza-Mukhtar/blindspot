import pytest
import impl


def test_argument_validation_header_not_string():
    """header must be a str, else ValueError"""
    with pytest.raises(ValueError):
        impl.resolve_range(123, 1000)


def test_argument_validation_length_not_int():
    """length must be an int, else ValueError"""
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-99", 1000.5)


def test_argument_validation_length_negative():
    """length must be non-negative, else ValueError"""
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-99", -1)


def test_argument_validation_length_zero():
    """length == 0 always raises UnsatisfiableRange"""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=0-99", 0)
    # Even malformed headers raise on empty representation
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("invalid", 0)


def test_single_range():
    """Single range specification resolves correctly"""
    assert impl.resolve_range("bytes=0-499", 1000) == [(0, 499)]


def test_multiple_ranges_preserve_order():
    """Multiple ranges preserve order, no merging or sorting"""
    result = impl.resolve_range("bytes=100-199,0-99,500-599", 1000)
    assert result == [(100, 199), (0, 99), (500, 599)]


def test_open_ended_range_from_first():
    """first- format ranges from first to end"""
    assert impl.resolve_range("bytes=100-", 1000) == [(100, 999)]
    assert impl.resolve_range("bytes=0-", 1000) == [(0, 999)]


def test_suffix_range():
    """-suffix format takes last suffix bytes"""
    assert impl.resolve_range("bytes=-100", 1000) == [(900, 999)]
    assert impl.resolve_range("bytes=-1", 1000) == [(999, 999)]


def test_suffix_greater_than_or_equal_length():
    """Suffix >= length yields whole representation"""
    assert impl.resolve_range("bytes=-5000", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=-1000", 1000) == [(0, 999)]


def test_last_beyond_length_clamped():
    """last >= length gets clamped to length-1"""
    assert impl.resolve_range("bytes=0-9999", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=500-10000", 1000) == [(500, 999)]


def test_single_and_last_byte_ranges():
    """Edge cases for single bytes and last byte"""
    assert impl.resolve_range("bytes=0-0", 1000) == [(0, 0)]
    assert impl.resolve_range("bytes=999-999", 1000) == [(999, 999)]


def test_unsatisfiable_first_beyond_length():
    """first >= length is unsatisfiable, raises when all specs unsatisfiable"""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=5000-5100", 1000)


def test_unsatisfiable_suffix_zero():
    """-0 asks for last zero bytes, which is unsatisfiable"""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-0", 1000)


def test_unsatisfiable_mixed_with_satisfiable():
    """Unsatisfiable specs dropped when some satisfiable remain"""
    result = impl.resolve_range("bytes=100-199,5000-5100,0-0", 1000)
    assert result == [(100, 199), (0, 0)]


def test_whitespace_and_empty_elements():
    """Spaces/tabs around header and elements are ignored; empty elements skipped"""
    assert impl.resolve_range("  bytes=0-99  ", 1000) == [(0, 99)]
    assert impl.resolve_range("bytes=0-99, 200-299", 1000) == [(0, 99), (200, 299)]
    assert impl.resolve_range("bytes=0-99,\t200-299", 1000) == [(0, 99), (200, 299)]
    assert impl.resolve_range("bytes=0-0,,1-1", 1000) == [(0, 0), (1, 1)]


def test_case_insensitive_unit():
    """Unit 'bytes' is case-insensitive"""
    assert impl.resolve_range("Bytes=0-99", 1000) == [(0, 99)]
    assert impl.resolve_range("BYTES=0-99", 1000) == [(0, 99)]
    assert impl.resolve_range("bYtEs=0-99", 1000) == [(0, 99)]


def test_leading_zeroes_allowed():
    """Leading zeroes in numbers are legal and meaningless"""
    assert impl.resolve_range("bytes=007-009", 1000) == [(7, 9)]
    assert impl.resolve_range("bytes=00-000", 1000) == [(0, 0)]


def test_malformed_headers_return_whole_object():
    """Malformed headers are ignored entirely, serve whole representation"""
    # Empty string
    assert impl.resolve_range("", 1000) == [(0, 999)]
    # Missing equals
    assert impl.resolve_range("bytes0-99", 1000) == [(0, 999)]
    # Wrong unit
    assert impl.resolve_range("items=0-99", 1000) == [(0, 999)]
    # Non-digits
    assert impl.resolve_range("bytes=abc-def", 1000) == [(0, 999)]
    # Plus sign
    assert impl.resolve_range("bytes=+5-9", 1000) == [(0, 999)]
    # Semicolon in spec
    assert impl.resolve_range("bytes=0-1;q=1", 1000) == [(0, 999)]
    # Bare dash
    assert impl.resolve_range("bytes=-", 1000) == [(0, 999)]
    # Just equals, no specs
    assert impl.resolve_range("bytes=", 1000) == [(0, 999)]


def test_malformed_bad_element_poisons_entire_header():
    """One bad element poisons the whole header"""
    # last < first is invalid
    assert impl.resolve_range("bytes=5-3", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=0-1,5-3", 1000) == [(0, 999)]
    # Space after equals
    assert impl.resolve_range("bytes= 0-99", 1000) == [(0, 999)]
    # Space before equals
    assert impl.resolve_range("bytes =0-99", 1000) == [(0, 999)]
    # Space inside spec
    assert impl.resolve_range("bytes=0 - 99", 1000) == [(0, 999)]
