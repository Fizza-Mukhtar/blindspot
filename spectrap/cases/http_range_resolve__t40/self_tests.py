import pytest
import impl


def test_arg_validation_header_type():
    """header must be a str."""
    with pytest.raises(ValueError):
        impl.resolve_range(123, 100)


def test_arg_validation_length_type():
    """length must be an int."""
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-1", "100")


def test_arg_validation_length_negative():
    """length must be non-negative."""
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-1", -1)


def test_zero_length_raises_unsatisfiable():
    """length=0 raises UnsatisfiableRange regardless of header."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=0-0", 0)


def test_zero_length_malformed_header_raises():
    """length=0 raises UnsatisfiableRange even for malformed header."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("invalid", 0)


def test_closed_range():
    """Closed range first-last."""
    assert impl.resolve_range("bytes=0-99", 1000) == [(0, 99)]


def test_open_range_to_end():
    """Open range first- extends to end."""
    assert impl.resolve_range("bytes=500-", 1000) == [(500, 999)]


def test_suffix_range():
    """Suffix range -suffix gives last N bytes."""
    assert impl.resolve_range("bytes=-100", 1000) == [(900, 999)]


def test_multiple_ranges_order_preserved():
    """Multiple ranges stay in order, not merged or deduplicated."""
    result = impl.resolve_range("bytes=0-99,200-299,500-599", 1000)
    assert result == [(0, 99), (200, 299), (500, 599)]


def test_clamp_last_beyond_representation():
    """last >= length clamped to length - 1."""
    assert impl.resolve_range("bytes=0-9999", 1000) == [(0, 999)]


def test_clamp_suffix_beyond_representation():
    """suffix >= length yields whole representation."""
    assert impl.resolve_range("bytes=-5000", 1000) == [(0, 999)]


def test_first_beyond_length_unsatisfiable():
    """first >= length is unsatisfiable; all unsatisfiable raises."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=1000-1999", 1000)


def test_suffix_zero_unsatisfiable():
    """-0 is unsatisfiable."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-0", 1000)


def test_unsatisfiable_dropped_satisfiable_kept():
    """Unsatisfiable specs dropped, satisfiable kept in order."""
    result = impl.resolve_range("bytes=100-199,5000-5100,0-0", 1000)
    assert result == [(100, 199), (0, 0)]


def test_unrecognized_unit():
    """Unrecognized unit returns whole object."""
    assert impl.resolve_range("items=0-99", 1000) == [(0, 999)]


def test_case_insensitive_unit():
    """Unit is case-insensitive."""
    assert impl.resolve_range("Bytes=0-99", 1000) == [(0, 99)]


def test_spaces_around_equals_forbidden():
    """Spaces around = are not allowed."""
    assert impl.resolve_range("bytes = 0-99", 1000) == [(0, 999)]


def test_spaces_inside_spec_forbidden():
    """Spaces inside spec are not allowed."""
    assert impl.resolve_range("bytes=0 - 99", 1000) == [(0, 999)]


def test_grammar_error_poisons_header():
    """One grammar error poisons entire header."""
    assert impl.resolve_range("bytes=0-1,5-3", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=abc-def", 1000) == [(0, 999)]


def test_empty_elements_skipped():
    """Empty elements (consecutive commas) are skipped."""
    result = impl.resolve_range("bytes=0-0, ,-1", 1000)
    assert result == [(0, 0), (999, 999)]


def test_unsatisfiable_range_not_value_error():
    """UnsatisfiableRange is Exception, not ValueError."""
    assert issubclass(impl.UnsatisfiableRange, Exception)
    assert not issubclass(impl.UnsatisfiableRange, ValueError)
