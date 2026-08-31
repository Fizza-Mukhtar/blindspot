import pytest
import impl


def test_simple_closed_range():
    """Simple closed range: bytes=0-499"""
    result = impl.resolve_range("bytes=0-499", 1000)
    assert result == [(0, 499)]


def test_open_range_to_end():
    """Open-ended range: bytes=500-"""
    result = impl.resolve_range("bytes=500-", 1000)
    assert result == [(500, 999)]


def test_suffix_range():
    """Suffix range: bytes=-500"""
    result = impl.resolve_range("bytes=-500", 1000)
    assert result == [(500, 999)]


def test_single_byte_range():
    """Single byte: bytes=0-0"""
    result = impl.resolve_range("bytes=0-0", 1000)
    assert result == [(0, 0)]


def test_multiple_ranges():
    """Multiple comma-separated ranges preserve order"""
    result = impl.resolve_range("bytes=0-99,200-299,500-599", 1000)
    assert result == [(0, 99), (200, 299), (500, 599)]


def test_case_insensitive_unit():
    """Unit compares case-insensitively"""
    result = impl.resolve_range("Bytes=0-0", 100)
    assert result == [(0, 0)]


def test_leading_zeros():
    """Leading zeros are legal and meaningless"""
    result = impl.resolve_range("bytes=007-009", 100)
    assert result == [(7, 9)]


def test_last_clamped_to_length_minus_one():
    """Last greater than or equal to length is clamped"""
    result = impl.resolve_range("bytes=0-9999", 1000)
    assert result == [(0, 999)]


def test_suffix_beyond_length():
    """Suffix at or beyond length yields whole representation"""
    result = impl.resolve_range("bytes=-5000", 1000)
    assert result == [(0, 999)]


def test_mixed_satisfiable_and_unsatisfiable_specs():
    """Unsatisfiable specs dropped, satisfiable kept in order"""
    result = impl.resolve_range("bytes=100-199,5000-5100,0-0", 1000)
    assert result == [(100, 199), (0, 0)]


def test_header_not_string_raises_valueerror():
    """Non-string header raises ValueError"""
    with pytest.raises(ValueError, match="header must be a str"):
        impl.resolve_range(123, 1000)


def test_length_not_integer_raises_valueerror():
    """Non-integer length raises ValueError"""
    with pytest.raises(ValueError, match="length must be a non-negative int"):
        impl.resolve_range("bytes=0-99", "1000")


def test_zero_length_raises_unsatisfiable_range():
    """Empty representation (length=0) always raises UnsatisfiableRange"""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=0-99", 0)


def test_all_specs_unsatisfiable_raises():
    """All specs unsatisfiable raises UnsatisfiableRange"""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=5000-5100", 1000)


def test_suffix_zero_unsatisfiable():
    """Suffix -0 is unsatisfiable"""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-0", 1000)


def test_unknown_unit_serves_whole():
    """Unknown unit (not 'bytes') serves whole representation"""
    result = impl.resolve_range("items=0-5", 1000)
    assert result == [(0, 999)]


def test_non_digits_serves_whole():
    """Non-digit characters make header malformed"""
    result = impl.resolve_range("bytes=abc-100", 1000)
    assert result == [(0, 999)]


def test_missing_equals_serves_whole():
    """Missing = makes header malformed"""
    result = impl.resolve_range("bytes0-1", 1000)
    assert result == [(0, 999)]


def test_last_less_than_first_serves_whole():
    """Invalid spec (last < first) makes header malformed"""
    result = impl.resolve_range("bytes=5-3", 1000)
    assert result == [(0, 999)]


def test_spaces_around_equals_serves_whole():
    """Spaces around = make header malformed"""
    result = impl.resolve_range("bytes = 0-1", 1000)
    assert result == [(0, 999)]
