"""Authoritative examples for DATAX-238.

Every assertion here traces to a clause of the cited standard or to an explicit
sentence of SPEC.md, not to the reference implementation's behaviour.
``make verify-corpus`` runs this against ``reference.py`` in CI, which is what
lets the README claim that ground-truth labels are verified by construction
rather than by inspection.

Source: RFC 4180 section 2 (clauses 1, 2, 4, 5, 6, 7 and the ABNF grammar)
https://datatracker.ietf.org/doc/html/rfc4180#section-2
"""

import pytest

import impl


def test_records_are_delimited_by_crlf():
    """Clause 1: records are delimited by a line break (CRLF), not a bare LF."""
    out = impl.write_csv([["a"], ["b"]])
    assert out == "a\r\nb\r\n"
    assert "\n" not in out.replace("\r\n", "")


def test_final_record_is_also_terminated():
    """Clause 2 leaves it optional; SPEC.md pins it: every record is terminated."""
    assert impl.write_csv([["only"]]) == "only\r\n"
    assert impl.write_csv([["a", "b"], ["c", "d"]]).endswith("d\r\n")


def test_fields_are_comma_separated_with_no_trailing_comma():
    """Clause 4: 'The last field in the record must not be followed by a comma.'"""
    assert impl.write_csv([["a", "b", "c"]]) == "a,b,c\r\n"


def test_field_containing_a_comma_is_quoted():
    """Clause 6: fields containing commas should be enclosed in double quotes."""
    assert impl.write_csv([["Portland, OR"]]) == '"Portland, OR"\r\n'


def test_embedded_double_quote_is_escaped_by_doubling():
    """Clause 7: an inner double quote is escaped by preceding it with another."""
    assert impl.write_csv([['He said "hi"']]) == '"He said ""hi"""\r\n'


def test_double_quote_is_never_backslash_escaped():
    """Clause 7 names doubling as the only escape; a backslash is plain data."""
    out = impl.write_csv([['a"b']])
    assert out == '"a""b"\r\n'
    assert "\\" not in out


def test_lone_double_quote_field():
    """Clauses 6 and 7 together: enclose, then double the inner quote."""
    assert impl.write_csv([['"']]) == '""""\r\n'


def test_field_containing_crlf_is_quoted_and_preserved():
    """Clause 6: fields containing line breaks are enclosed; content is verbatim."""
    assert impl.write_csv([["line1\r\nline2"]]) == '"line1\r\nline2"\r\n'


def test_lone_cr_and_lone_lf_force_quoting_and_are_not_normalised():
    """ABNF: TEXTDATA admits neither CR nor LF, so `non-escaped` cannot hold one.

    SPEC.md states the character is preserved exactly, so a lone LF stays a
    lone LF inside the quotes.
    """
    assert impl.write_csv([["a\rb"]]) == '"a\rb"\r\n'
    assert impl.write_csv([["a\nb"]]) == '"a\nb"\r\n'


def test_spaces_are_data_and_do_not_trigger_quoting():
    """Clause 4: 'Spaces are considered part of a field and should not be ignored.'

    Combined with SPEC.md's if-and-only-if quoting rule, padding is written
    through unquoted and untrimmed.
    """
    assert impl.write_csv([["  keep  my  spaces  "]]) == "  keep  my  spaces  \r\n"
    assert impl.write_csv([[" a", "b "]]) == " a,b \r\n"


def test_field_of_only_spaces_is_written_verbatim():
    """Clause 4 again: whitespace-only is still ordinary field content."""
    assert impl.write_csv([["   "]]) == "   \r\n"


def test_padding_survives_when_the_field_is_quoted_for_another_reason():
    """Clause 4 (spaces kept) plus clause 6 (comma forces the quotes)."""
    assert impl.write_csv([["  a,b  "]]) == '"  a,b  "\r\n'


def test_non_trigger_characters_are_not_quoted():
    """SPEC.md: only comma, double quote, CR and LF cause a field to be quoted."""
    assert impl.write_csv([["semi;colon\ttab#hash"]]) == "semi;colon\ttab#hash\r\n"


def test_empty_field_is_written_as_nothing():
    """ABNF `non-escaped = *TEXTDATA` permits zero characters.

    SPEC.md: an empty field is written as nothing at all, not as `""`.
    """
    assert impl.write_csv([[""]]) == "\r\n"
    assert impl.write_csv([["", "", ""]]) == ",,\r\n"
    assert impl.write_csv([["a", "", "c"]]) == "a,,c\r\n"


def test_record_with_zero_fields_is_a_bare_crlf():
    """SPEC.md: a record with no fields writes just its CRLF."""
    assert impl.write_csv([[]]) == "\r\n"
    assert impl.write_csv([["a"], [], ["b"]]) == "a\r\n\r\nb\r\n"


def test_ragged_records_are_written_as_given():
    """Clause 4's equal-field-count rule is advisory; SPEC.md declines to enforce it."""
    assert impl.write_csv([["a"], ["b", "c"], ["d", "e", "f"]]) == "a\r\nb,c\r\nd,e,f\r\n"


def test_empty_table_returns_the_empty_string():
    """SPEC.md: if `rows` is empty, return the empty string."""
    assert impl.write_csv([]) == ""


def test_worked_example_from_the_ticket():
    """The exact example printed in SPEC.md."""
    given = [
        ["id", "comment", "owner"],
        ["1", 'She said "ship it"', "priya"],
        ["2", "Portland, OR", ""],
        ["3", "  keep  my  spaces  ", "dana"],
        [],
    ]
    assert impl.write_csv(given) == (
        "id,comment,owner\r\n"
        '1,"She said ""ship it""",priya\r\n'
        '2,"Portland, OR",\r\n'
        "3,  keep  my  spaces  ,dana\r\n"
        "\r\n"
    )


def test_input_is_not_mutated():
    """SPEC.md: the function is pure and must not mutate `rows`."""
    given = [["a", "b,c"], []]
    impl.write_csv(given)
    assert given == [["a", "b,c"], []]


@pytest.mark.parametrize("bad", [1, 0, None, True, 3.5, b"bytes", ["x"]])
def test_non_str_field_raises_type_error_naming_the_type(bad):
    """SPEC.md: every field must be a `str`; the message names the offending type."""
    with pytest.raises(TypeError) as excinfo:
        impl.write_csv([["ok"], ["fine", bad]])
    assert type(bad).__name__ in str(excinfo.value)
