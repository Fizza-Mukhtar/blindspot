"""Authoritative examples for CDN-2291.

Every assertion here is taken from the cited standard or from an explicit
sentence of SPEC.md, not from the reference implementation's behaviour.
``make verify-corpus`` runs this against ``reference.py`` in CI, which is what
lets the README claim that ground-truth labels are verified by construction
rather than by inspection.

Source: RFC 7233 sections 2.1 and 3.1, https://www.rfc-editor.org/rfc/rfc7233.html
"""

import pytest

import impl


def test_rfc_first_500_bytes_is_inclusive_on_both_ends():
    """RFC 7233 2.1, first bulleted example: 'The first 500 bytes' is bytes=0-499."""
    assert impl.resolve_range("bytes=0-499", 1000) == [(0, 499)]


def test_single_byte_range():
    """RFC 7233 2.1: first-byte-pos == last-byte-pos selects exactly one byte."""
    assert impl.resolve_range("bytes=0-0", 1000) == [(0, 0)]


def test_second_500_bytes():
    """RFC 7233 2.1, second bulleted example: 'The second 500 bytes'."""
    assert impl.resolve_range("bytes=500-999", 1000) == [(500, 999)]


def test_open_ended_spec_runs_to_the_end():
    """RFC 7233 2.1: an absent last-byte-pos means the remainder of the
    representation; 'bytes=9500-' is the RFC's own 'final 500 bytes' example."""
    assert impl.resolve_range("bytes=9500-", 10000) == [(9500, 9999)]
    assert impl.resolve_range("bytes=500-", 1000) == [(500, 999)]


def test_suffix_spec_selects_the_final_bytes():
    """RFC 7233 2.1: 'bytes=-500' is the other spelling of 'the final 500 bytes'."""
    assert impl.resolve_range("bytes=-500", 1000) == [(500, 999)]


def test_last_byte_pos_at_or_past_the_end_is_clamped_not_rejected():
    """RFC 7233 2.1: 'if the last-byte-pos value is ... greater than or equal to
    the current length ... it is interpreted as [current length] - 1'."""
    assert impl.resolve_range("bytes=0-9999", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=999-999", 1000) == [(999, 999)]
    assert impl.resolve_range("bytes=900-1000", 1000) == [(900, 999)]


def test_suffix_longer_than_the_representation_yields_the_whole_object():
    """RFC 7233 2.1: 'if ... the suffix-length is greater than the current
    length ... the entire representation is used'."""
    assert impl.resolve_range("bytes=-5000", 1000) == [(0, 999)]
    assert impl.resolve_range("bytes=-1000", 1000) == [(0, 999)]


def test_zero_length_suffix_is_unsatisfiable():
    """RFC 7233 2.1: a byte-range-set is satisfiable only if it holds a
    suffix-byte-range-spec with a NON-ZERO suffix-length (or a usable
    first-byte-pos), so 'bytes=-0' on its own is a 416."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=-0", 1000)


def test_first_byte_pos_at_or_past_the_end_is_unsatisfiable():
    """RFC 7233 2.1: satisfiability requires a first-byte-pos 'less than the
    current length of the selected representation'."""
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=1000-1200", 1000)
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=1000-", 1000)


def test_unsatisfiable_specs_are_dropped_when_another_is_satisfiable():
    """SPEC.md, 'Combining the results': unsatisfiable specs are dropped
    silently as long as at least one spec is satisfiable, and the survivors
    keep their original relative order."""
    assert impl.resolve_range("bytes=100-199,5000-5100,0-0", 1000) == [(100, 199), (0, 0)]
    assert impl.resolve_range("bytes=-0,-1", 1000) == [(999, 999)]


def test_ranges_are_neither_coalesced_nor_reordered():
    """SPEC.md, 'What to build': one pair per requested range, in header order,
    with no merging, sorting or de-duplication."""
    assert impl.resolve_range("bytes=0-99,50-149", 1000) == [(0, 99), (50, 149)]
    assert impl.resolve_range("bytes=500-599,0-9", 1000) == [(500, 599), (0, 9)]
    assert impl.resolve_range("bytes=0-9,0-9", 1000) == [(0, 9), (0, 9)]


def test_rfc_first_and_last_byte_idiom():
    """RFC 7233 2.1, final bulleted example: 'bytes=0-0,-1' selects the first
    and last bytes only."""
    assert impl.resolve_range("bytes=0-0,-1", 1000) == [(0, 0), (999, 999)]


def test_optional_whitespace_and_empty_list_elements():
    """RFC 7230 section 7 list rule, as restated in SPEC.md's 'Header syntax we
    accept': OWS around elements is allowed and empty elements are skipped."""
    assert impl.resolve_range("bytes=0-0, ,-1", 1000) == [(0, 0), (999, 999)]
    assert impl.resolve_range("  bytes=0-0 ,\t500-599  ", 1000) == [(0, 0), (500, 599)]


def test_case_insensitive_unit_and_leading_zeroes():
    """SPEC.md, 'Header syntax we accept': the unit token is compared
    case-insensitively and leading zeroes carry no meaning."""
    assert impl.resolve_range("Bytes=0-0", 1000) == [(0, 0)]
    assert impl.resolve_range("bytes=007-009", 1000) == [(7, 9)]


@pytest.mark.parametrize(
    "header",
    [
        "",
        "0-499",
        "bytes",
        "bytes=",
        "bytes=abc",
        "bytes=-",
        "bytes = 0-1",
        "bytes=0 - 1",
        "bytes=+5-9",
        "bytes=0-1;q=1",
        "items=0-5",
        "bytes=2-1",
        "bytes=0-1,5-3",
    ],
)
def test_malformed_or_unknown_unit_headers_are_ignored(header):
    """RFC 7233 3.1 ('An origin server MUST ignore a Range header field that
    contains a range unit it does not understand') and RFC 7233 2.1 ('A
    byte-range-spec is invalid if the last-byte-pos value is present and less
    than the first-byte-pos'), as resolved by SPEC.md's 'Malformed headers are
    ignored, not rejected': the whole representation comes back."""
    assert impl.resolve_range(header, 1000) == [(0, 999)]


def test_zero_length_representation_is_always_unsatisfiable():
    """SPEC.md, 'Arguments and errors': length 0 raises whatever the header
    says, including for a header that would otherwise be ignored."""
    for header in ("bytes=0-0", "bytes=-1", "bytes=0-", "banana", ""):
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range(header, 0)


def test_unsatisfiable_range_is_not_a_value_error():
    """SPEC.md, 'Combining the results': UnsatisfiableRange derives from
    Exception directly, because ValueError means 400 and this means 416."""
    assert issubclass(impl.UnsatisfiableRange, Exception)
    assert not issubclass(impl.UnsatisfiableRange, ValueError)


@pytest.mark.parametrize("bad_args", [("bytes=0-0", -1), (b"bytes=0-0", 1000), ("bytes=0-0", "1000")])
def test_invalid_arguments_raise_value_error(bad_args):
    """SPEC.md, 'Arguments and errors': header must be a str and length a
    non-negative int; anything else is a ValueError."""
    with pytest.raises(ValueError):
        impl.resolve_range(*bad_args)


def test_single_byte_object():
    """SPEC.md boundary: with length 1 the only byte is (0, 0), a suffix of any
    non-zero size yields it, and any first-byte-pos of 1 or more is a 416."""
    assert impl.resolve_range("bytes=0-", 1) == [(0, 0)]
    assert impl.resolve_range("bytes=-9", 1) == [(0, 0)]
    with pytest.raises(impl.UnsatisfiableRange):
        impl.resolve_range("bytes=1-", 1)
