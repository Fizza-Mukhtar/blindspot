import pytest

import impl


def test_empty_rows_returns_empty_string():
    assert impl.write_csv([]) == ""


def test_worked_example_from_ticket():
    rows = [
        ["id", "comment", "owner"],
        ["1", 'She said "ship it"', "priya"],
        ["2", "Portland, OR", ""],
        ["3", "  keep  my  spaces  ", "dana"],
        [],
    ]
    expected = (
        'id,comment,owner\r\n'
        '1,"She said ""ship it""",priya\r\n'
        '2,"Portland, OR",\r\n'
        '3,  keep  my  spaces  ,dana\r\n'
        '\r\n'
    )
    assert impl.write_csv(rows) == expected


def test_simple_no_special_chars_unquoted():
    rows = [["a", "b", "c"], ["1", "2", "3"]]
    assert impl.write_csv(rows) == "a,b,c\r\n1,2,3\r\n"


def test_field_with_comma_is_quoted():
    rows = [["Portland, OR"]]
    assert impl.write_csv(rows) == '"Portland, OR"\r\n'


def test_field_with_double_quote_is_quoted_and_doubled():
    rows = [['a"b']]
    assert impl.write_csv(rows) == '"a""b"\r\n'


def test_lone_double_quote_field_becomes_four_quote_chars():
    rows = [['"']]
    assert impl.write_csv(rows) == '""""\r\n'


def test_field_with_embedded_crlf_is_quoted_and_preserved():
    rows = [["line1\r\nline2"]]
    assert impl.write_csv(rows) == '"line1\r\nline2"\r\n'


def test_field_with_lone_cr_is_quoted_and_not_normalised():
    rows = [["a\rb"]]
    result = impl.write_csv(rows)
    assert result == '"a\rb"\r\n'
    # The lone CR must survive untouched inside the quoted field.
    assert "a\rb" in result


def test_field_with_lone_lf_is_quoted_and_not_normalised():
    rows = [["a\nb"]]
    result = impl.write_csv(rows)
    assert result == '"a\nb"\r\n'
    assert "a\nb" in result


def test_leading_and_trailing_spaces_preserved_unquoted():
    rows = [["  0041"], ["0041  "], ["  keep  my  spaces  "]]
    assert impl.write_csv(rows) == "  0041\r\n0041  \r\n  keep  my  spaces  \r\n"


def test_field_that_is_only_spaces_is_unquoted():
    rows = [["   "]]
    assert impl.write_csv(rows) == "   \r\n"


def test_tab_semicolon_hash_and_nonascii_are_unquoted():
    rows = [["a\tb", "x;y", "#tag", "caf\u00e9"]]
    assert impl.write_csv(rows) == "a\tb,x;y,#tag,caf\u00e9\r\n"


def test_empty_field_written_as_nothing_not_quotes():
    rows = [["", "", ""]]
    assert impl.write_csv(rows) == ",,\r\n"


def test_zero_field_record_is_blank_line():
    rows = [["a", "b"], [], ["c"]]
    assert impl.write_csv(rows) == "a,b\r\n\r\nc\r\n"


def test_ragged_records_are_not_padded_or_rejected():
    rows = [["a", "b", "c"], ["x"], ["y", "z"]]
    assert impl.write_csv(rows) == "a,b,c\r\nx\r\ny,z\r\n"


def test_output_always_ends_with_crlf_when_nonempty():
    rows = [["only"]]
    result = impl.write_csv(rows)
    assert result.endswith("\r\n")
    assert result == "only\r\n"


def test_does_not_mutate_input_rows_or_records():
    rows = [["a", "b"], ["c, d", 'e"f']]
    original = [list(r) for r in rows]
    impl.write_csv(rows)
    assert rows == original


def test_typeerror_for_int_field_names_type_in_message():
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([["a", 1]])
    assert "int" in str(exc_info.value)


def test_typeerror_for_none_field():
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[None]])
    assert "NoneType" in str(exc_info.value)


def test_typeerror_for_bool_field_not_stringified():
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([["a", True]])
    assert "bool" in str(exc_info.value)
