import impl
import pytest


def test_empty_rows():
    """Empty input returns empty string."""
    assert impl.write_csv([]) == ""


def test_single_field_single_row():
    """Simple case: one record, one field."""
    assert impl.write_csv([["hello"]]) == "hello\r\n"


def test_multiple_fields_single_row():
    """One record with multiple fields."""
    assert impl.write_csv([["a", "b", "c"]]) == "a,b,c\r\n"


def test_multiple_rows():
    """Multiple records."""
    result = impl.write_csv([["1", "2"], ["3", "4"]])
    assert result == "1,2\r\n3,4\r\n"


def test_empty_field():
    """Empty field is not quoted."""
    result = impl.write_csv([["", "x", ""]])
    assert result == ",x,\r\n"


def test_all_empty_fields():
    """Record with all empty fields."""
    result = impl.write_csv([["", "", ""]])
    assert result == ",,\r\n"


def test_empty_record():
    """Record with no fields produces just CRLF."""
    result = impl.write_csv([[]])
    assert result == "\r\n"


def test_field_with_comma():
    """Field containing comma must be quoted."""
    result = impl.write_csv([["Portland, OR"]])
    assert result == '"Portland, OR"\r\n'


def test_field_with_quote():
    """Field containing quote is quoted and interior quotes doubled."""
    result = impl.write_csv([['He said "hi"']])
    assert result == '"He said ""hi"""\r\n'


def test_field_single_quote():
    """Field that is a single quote becomes four quotes."""
    result = impl.write_csv([['"']])
    assert result == '""""\r\n'


def test_field_with_cr():
    """Field containing CR must be quoted."""
    result = impl.write_csv([["line1\rline2"]])
    assert result == '"line1\rline2"\r\n'


def test_field_with_lf():
    """Field containing LF must be quoted."""
    result = impl.write_csv([["line1\nline2"]])
    assert result == '"line1\nline2"\r\n'


def test_field_with_crlf():
    """Field containing CRLF must be quoted."""
    result = impl.write_csv([["line1\r\nline2"]])
    assert result == '"line1\r\nline2"\r\n'


def test_ticket_example():
    """Verify example from ticket specification."""
    result = impl.write_csv([["2", "Portland, OR", ""], []])
    assert result == '2,"Portland, OR",\r\n\r\n'


def test_non_trigger_characters():
    """Spaces, tabs, semicolons, hashes, backslashes are not quoting triggers."""
    result = impl.write_csv([["  spaces  ", "tab\there", "value;here", "#hash", "C:\\path"]])
    assert result == "  spaces  ,tab\there,value;here,#hash,C:\\path\r\n"


def test_multiple_quotes():
    """Multiple quotes in field are all doubled."""
    result = impl.write_csv([['a"b"c"d']])
    assert result == '"a""b""c""d"\r\n'


def test_type_error_integer():
    """Integer field raises TypeError containing 'int'."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[42]])
    assert "int" in str(exc_info.value)


def test_type_error_various_types():
    """Non-string types (None, bool, bytes) raise TypeError."""
    with pytest.raises(TypeError):
        impl.write_csv([[None]])
    with pytest.raises(TypeError):
        impl.write_csv([[True]])
    with pytest.raises(TypeError):
        impl.write_csv([[b"bytes"]])


def test_type_error_detection_in_row():
    """Type errors are caught in fields and rows after the first."""
    with pytest.raises(TypeError):
        impl.write_csv([["valid", 123]])
    with pytest.raises(TypeError):
        impl.write_csv([["valid"], [456]])


def test_immutability():
    """Input rows and records are not mutated."""
    rows = [["a", "b"], ["c", "d"]]
    rows_copy = [list(row) for row in rows]
    impl.write_csv(rows)
    assert rows == rows_copy
