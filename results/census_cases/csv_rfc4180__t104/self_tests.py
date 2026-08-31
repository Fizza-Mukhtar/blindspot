import impl
import pytest


# Basic functionality
def test_empty_rows():
    """Empty rows list returns empty string."""
    assert impl.write_csv([]) == ""


def test_single_field():
    """Single field in a row ends with CRLF."""
    assert impl.write_csv([["hello"]]) == "hello\r\n"


def test_multiple_fields_and_rows():
    """Multiple fields and rows are properly formatted."""
    result = impl.write_csv([["a", "b", "c"], ["1", "2", "3"]])
    assert result == "a,b,c\r\n1,2,3\r\n"


def test_example_from_ticket():
    """Example from ticket specification."""
    result = impl.write_csv([["2", "Portland, OR", ""], []])
    assert result == '2,"Portland, OR",\r\n\r\n'


# Empty fields and records
def test_empty_fields():
    """Empty fields output as zero characters."""
    result = impl.write_csv([["a", "", "b"], ["", "", ""]])
    assert result == "a,,b\r\n,,\r\n"


def test_empty_row():
    """Empty row (no fields) outputs just CRLF."""
    result = impl.write_csv([[]])
    assert result == "\r\n"


# Quoting: fields that need quoting
def test_quoting_with_comma():
    """Field with comma is quoted."""
    result = impl.write_csv([["hello, world"]])
    assert result == '"hello, world"\r\n'


def test_quoting_with_quotes():
    """Field with double quotes is quoted and inner quotes are doubled."""
    result = impl.write_csv([['He said "hi"']])
    assert result == '"He said ""hi"""\r\n'


def test_quoting_with_cr_and_lf():
    """Fields with CR, LF, or CRLF are quoted and preserved as-is."""
    result = impl.write_csv([["line1\r\nline2"], ["lone\r"], ["lone\n"]])
    assert result == '"line1\r\nline2"\r\n"lone\r"\r\n"lone\n"\r\n'


def test_single_quote_field():
    """A field that is just a double quote is output as four quotes."""
    result = impl.write_csv([['"']])
    assert result == '""""\r\n'


# Non-quoting: fields that don't need quoting
def test_no_quoting_for_spaces_and_other_chars():
    """Spaces, tabs, semicolons, etc. are not quoting triggers."""
    result = impl.write_csv([
        ["  spaces  "],
        ["hello\tworld"],
        ["hello;world"],
        ["hello#world"],
        ["hello\\world"],
        ["caf\u00e9"],
    ])
    assert result == (
        "  spaces  \r\n"
        "hello\tworld\r\n"
        "hello;world\r\n"
        "hello#world\r\n"
        "hello\\world\r\n"
        "caf\u00e9\r\n"
    )


def test_ragged_records():
    """Ragged records (different field counts) are preserved."""
    result = impl.write_csv([["a", "b", "c"], ["x"], ["1", "2"]])
    assert result == "a,b,c\r\nx\r\n1,2\r\n"


def test_mixed_quoted_and_unquoted():
    """Some fields quoted, others not, in the same row."""
    result = impl.write_csv([["plain", "has,comma", "normal", '"quoted"']])
    assert result == 'plain,"has,comma",normal,"""quoted"""\r\n'


# Type validation
def test_type_error_int():
    """Non-string field (int) raises TypeError with type name."""
    with pytest.raises(TypeError, match="int"):
        impl.write_csv([[123]])


def test_type_error_non_string():
    """Non-string fields (bool, None, bytes, etc.) raise TypeError."""
    for value, type_name in [(True, "bool"), (None, "NoneType"), (b"bytes", "bytes"), ([], "list")]:
        with pytest.raises(TypeError, match=type_name):
            impl.write_csv([[value]])


def test_all_records_end_with_crlf():
    """Every record, including the last, ends with CRLF."""
    result = impl.write_csv([["a"], ["b"], ["c"]])
    assert result == "a\r\nb\r\nc\r\n"
    assert result.endswith("\r\n")
    assert result.count("\r\n") == 3


def test_pure_function_no_mutation():
    """Function does not mutate the input rows."""
    rows = [["a", "b,c"], ["d"]]
    rows_copy = [row[:] for row in rows]
    impl.write_csv(rows)
    assert rows == rows_copy
