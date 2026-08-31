import impl
import pytest


def test_single_range():
    """Single range request."""
    assert impl.resolve_range("bytes=0-499", 1000) == [(0, 499)]


def test_multiple_ranges():
    """Multiple comma-separated ranges."""
    assert impl.resolve_range("bytes=0-99,200-299", 1000) == [(0, 99), (200, 299)]


def test_open_ended_range():
    """Range from position to end (first-)."""
    assert impl.resolve_range("bytes=500-", 1000) == [(500, 999)]


def test_suffix_range():
    """Last N bytes (-suffix)."""
    assert impl.resolve_range("bytes=-500", 1000) == [(500, 999)]


def test_single_byte():
    """Single byte range."""
    assert impl.resolve_range("bytes=0-0", 100) == [(0, 0)]


def test_last_byte():
    """Last byte of representation."""
    assert impl.resolve_range("bytes=99-", 100) == [(99, 99)]


def test_last_clamped():
    """End byte beyond length is clamped."""
    assert impl.resolve_range("bytes=0-9999", 100) == [(0, 99)]


def test_suffix_beyond_length():
    """Suffix beyond length returns whole object."""
    assert impl.resolve_range("bytes=-5000", 100) == [(0, 99)]


def test_leading_zeros():
    """Leading zeros in numbers are legal."""
    assert impl.resolve_range("bytes=007-009", 100) == [(7, 9)]


def test_case_insensitive():
    """Unit comparison is case-insensitive."""
    assert impl.resolve_range("Bytes=0-99", 1000) == [(0, 99)]
    assert impl.resolve_range("BYTES=0-99", 1000) == [(0, 99)]


def test_whitespace_around_specs():
    """Whitespace around specs is allowed."""
    assert impl.resolve_range("bytes=0-99, 200-299", 1000) == [(0, 99), (200, 299)]
    assert impl.resolve_range("  bytes=0-99  ", 1000) == [(0, 99)]
    assert impl.resolve_range("bytes=0-0,,200-299", 1000) == [(0, 0), (200, 299)]


def test_unsatisfiable_suffix_zero():
    """-0 is unsatisfiable."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-0", 100)


def test_unsatisfiable_first_exceeds():
    """first >= length is unsatisfiable."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=1000-1999", 1000)


def test_unsatisfiable_mixed():
    """Unsatisfiable specs dropped if some satisfiable."""
    assert impl.resolve_range("bytes=100-199,5000-5100,0-0", 1000) == [(100, 199), (0, 0)]
    assert impl.resolve_range("bytes=100-199,-0", 1000) == [(100, 199)]


def test_unsatisfiable_all():
    """All specs unsatisfiable raises."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=5000-5100,-0", 1000)
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-0,-0", 100)


def test_malformed_wrong_unit():
    """Wrong unit returns whole object."""
    assert impl.resolve_range("items=0-499", 1000) == [(0, 999)]


def test_malformed_bare_dash():
    """Bare dash or empty range returns whole object."""
    assert impl.resolve_range("bytes=-", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=abc-def", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes0-499", 1000) == [(0, 999)]


def test_malformed_invalid_range():
    """Invalid range format returns whole object."""
    assert impl.resolve_range("bytes=5-3", 1000) == [(0, 999)]  # last < first
    assert impl.resolve_range("bytes=0-1,5-3", 1000) == [(0, 999)]  # bad element poisons all
    assert impl.resolve_range("bytes=+5-9", 1000) == [(0, 999)]  # plus sign


def test_argument_validation():
    """Argument validation raises ValueError."""
    with pytest.raises(ValueError):
        impl.resolve_range(123, 1000)
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-499", 1000.5)
    with pytest.raises(ValueError):
        impl.resolve_range("bytes=0-499", -1)


def test_empty_representation():
    """Empty representation always raises UnsatisfiableRange."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=0-499", 0)
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("", 0)
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-", 0)
