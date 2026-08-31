import copy
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


def test_zero_field_record_is_just_crlf():
    assert impl.write_csv([[]]) == "\r\n"


def test_three_empty_fields_record():
    assert impl.write_csv([["", "", ""]]) == ",,\r\n"


def test_single_field_record_no_trailing_comma():
    assert impl.write_csv([["onlyfield"]]) == "onlyfield\r\n"


def test_last_field_not_followed_by_comma_multi_field():
    assert impl.write_csv([["a", "b", "c"]]) == "a,b,c\r\n"


def test_comma_triggers_quoting():
    assert impl.write_csv([["a,b"]]) == '"a,b"\r\n'


def test_double_quote_triggers_quoting_and_is_doubled():
    assert impl.write_csv([['a"b']]) == '"a""b"\r\n'


def test_lone_quote_character_field():
    assert impl.write_csv([['"']]) == '""""\r\n'


def test_crlf_inside_field_triggers_quoting_and_is_preserved():
    assert impl.write_csv([["a\r\nb"]]) == '"a\r\nb"\r\n'


def test_lone_cr_and_lone_lf_trigger_quoting_and_are_preserved_verbatim():
    assert impl.write_csv([["a\rb"]]) == '"a\rb"\r\n'
    assert impl.write_csv([["a\nb"]]) == '"a\nb"\r\n'


def test_spaces_are_preserved_unquoted():
    assert impl.write_csv([["  0041"]]) == "  0041\r\n"
    assert impl.write_csv([["0041  "]]) == "0041  \r\n"
    assert impl.write_csv([["   "]]) == "   \r\n"
    assert impl.write_csv([["a   b"]]) == "a   b\r\n"


def test_non_trigger_special_characters_stay_unquoted():
    assert impl.write_csv([["a\tb"]]) == "a\tb\r\n"
    assert impl.write_csv([["a;b"]]) == "a;b\r\n"
    assert impl.write_csv([["#comment"]]) == "#comment\r\n"
    assert impl.write_csv([["caf\u00e9"]]) == "caf\u00e9\r\n"


def test_ragged_records_written_with_own_field_counts():
    rows = [["a", "b", "c"], ["x"], ["p", "q"]]
    assert impl.write_csv(rows) == "a,b,c\r\nx\r\np,q\r\n"


@pytest.mark.parametrize(
    "bad_value, expected_type_name",
    [
        (42, "int"),
        (None, "NoneType"),
        (b"bytes", "bytes"),
        (True, "bool"),
        (3.14, "float"),
    ],
)
def test_non_str_field_raises_type_error_naming_the_type(bad_value, expected_type_name):
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([["ok", bad_value]])
    assert expected_type_name in str(exc_info.value)


def test_does_not_mutate_input_rows():
    rows = [["a", 'b"c'], ["  x  ", ""]]
    original = copy.deepcopy(rows)
    impl.write_csv(rows)
    assert rows == original


def test_multiple_normal_records_all_terminated_with_crlf():
    rows = [["h1", "h2"], ["v1", "v2"], ["v3", "v4"]]
    result = impl.write_csv(rows)
    assert result == "h1,h2\r\nv1,v2\r\nv3,v4\r\n"
    assert result.endswith("\r\n")
    assert "\n" not in result.replace("\r\n", "")
