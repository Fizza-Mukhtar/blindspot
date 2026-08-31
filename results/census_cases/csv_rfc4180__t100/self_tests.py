import impl
import pytest


def test_empty_rows():
    """Empty rows list returns empty string."""
    assert impl.write_csv([]) == ""


def test_single_field_basic():
    """Single field without special characters."""
    assert impl.write_csv([["hello"]]) == "hello\r\n"


def test_multiple_fields_basic():
    """Multiple fields without special characters."""
    assert impl.write_csv([["a", "b", "c"]]) == "a,b,c\r\n"


def test_multiple_records():
    """Multiple records are joined with CRLF."""
    assert impl.write_csv([["a"], ["b"], ["c"]]) == "a\r\nb\r\nc\r\n"


def test_field_with_comma_requires_quoting():
    """Field containing comma must be quoted."""
    assert impl.write_csv([["Portland, OR"]]) == '"Portland, OR"\r\n'


def test_field_with_quote_requires_quoting_and_escaping():
    """Field containing quote is quoted and interior quotes doubled."""
    assert impl.write_csv([['He said "hi"']]) == '"He said ""hi"""\r\n'


def test_field_with_cr_requires_quoting():
    """Field containing CR must be quoted and preserved."""
    assert impl.write_csv([["line1\rline2"]]) == '"line1\rline2"\r\n'


def test_field_with_lf_requires_quoting():
    """Field containing LF must be quoted and preserved."""
    assert impl.write_csv([["line1\nline2"]]) == '"line1\nline2"\r\n'


def test_spaces_tabs_not_quoted():
    """Spaces and tabs are not quoting triggers."""
    assert impl.write_csv([["  hello\tworld  "]]) == "  hello\tworld  \r\n"


def test_non_ascii_not_quoted():
    """Non-ASCII characters are not quoting triggers."""
    assert impl.write_csv([["café"]]) == "café\r\n"


def test_single_empty_field():
    """Single empty field produces record with just CRLF."""
    assert impl.write_csv([[""]]) == "\r\n"


def test_multiple_empty_fields():
    """Multiple empty fields are represented by commas."""
    assert impl.write_csv([["", "", ""]]) == ",,\r\n"


def test_empty_record():
    """Empty record (no fields) produces just CRLF."""
    assert impl.write_csv([[]]) == "\r\n"


def test_ticket_example():
    """Comprehensive example from ticket specification."""
    result = impl.write_csv([["2", "Portland, OR", ""], []])
    assert result == '2,"Portland, OR",\r\n\r\n'


def test_field_with_quote_and_comma():
    """Field with both quote and comma triggers quoting."""
    result = impl.write_csv([['He said "yes, definitely"']])
    assert result == '"He said ""yes, definitely"""\r\n'


def test_type_error_int():
    """Integer field raises TypeError containing 'int'."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[42]])
    assert "int" in str(exc_info.value)


def test_type_error_none():
    """None field raises TypeError containing 'NoneType'."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[None]])
    assert "NoneType" in str(exc_info.value)


def test_type_error_bool():
    """Boolean field raises TypeError containing 'bool'."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[False]])
    assert "bool" in str(exc_info.value)


def test_type_error_bytes():
    """Bytes field raises TypeError containing 'bytes'."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[b"data"]])
    assert "bytes" in str(exc_info.value)


def test_ragged_records():
    """Records with different field counts are allowed."""
    result = impl.write_csv([["a", "b"], ["c"], ["d", "e", "f"]])
    assert result == "a,b\r\nc\r\nd,e,f\r\n"
