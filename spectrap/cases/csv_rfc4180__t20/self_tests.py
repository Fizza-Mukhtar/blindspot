import pytest
import impl


def test_empty_rows():
    """Empty rows returns empty string."""
    assert impl.write_csv([]) == ""


def test_single_field():
    """Single record with single field."""
    assert impl.write_csv([["hello"]]) == "hello\r\n"


def test_multiple_records():
    """Multiple records are separated by CRLF."""
    result = impl.write_csv([["a"], ["b"], ["c"]])
    assert result == "a\r\nb\r\nc\r\n"


def test_multiple_fields_in_record():
    """Multiple fields in a record are comma-separated."""
    assert impl.write_csv([["a", "b", "c"]]) == "a,b,c\r\n"


def test_empty_fields():
    """Empty fields are preserved as zero characters."""
    result = impl.write_csv([["2", "Portland, OR", ""]])
    assert result == '2,"Portland, OR",\r\n'


def test_empty_record():
    """Record with no fields writes just CRLF."""
    assert impl.write_csv([[]]) == "\r\n"


def test_field_with_comma():
    """Field containing comma is quoted."""
    assert impl.write_csv([["Portland, OR"]]) == '"Portland, OR"\r\n'


def test_field_with_double_quote():
    """Field containing double quote is quoted and doubled."""
    result = impl.write_csv([['He said "hi"']])
    assert result == '"He said ""hi"""\r\n'


def test_single_quote_character():
    """Single double-quote field becomes four quotes."""
    assert impl.write_csv([['"']]) == '""""\r\n'


def test_field_with_crlf():
    """Field containing CRLF is quoted."""
    result = impl.write_csv([["line1\r\nline2"]])
    assert result == '"line1\r\nline2"\r\n'


def test_field_with_lone_cr_or_lf():
    """Field containing lone CR or LF is quoted and preserved."""
    assert impl.write_csv([["before\rafter"]]) == '"before\rafter"\r\n'
    assert impl.write_csv([["before\nafter"]]) == '"before\nafter"\r\n'


def test_spaces_are_not_quoted():
    """Spaces (including multiple spaces) do not trigger quoting."""
    assert impl.write_csv([["  keep  my  spaces  "]]) == "  keep  my  spaces  \r\n"
    assert impl.write_csv([["   "]]) == "   \r\n"


def test_tabs_semicolons_backslashes_not_quoted():
    """Tabs, semicolons, backslashes do not trigger quoting."""
    assert impl.write_csv([["tab\there"]]) == "tab\there\r\n"
    assert impl.write_csv([["semi;colon"]]) == "semi;colon\r\n"
    assert impl.write_csv([["back\\slash"]]) == "back\\slash\r\n"


def test_multiple_consecutive_quotes():
    """Multiple consecutive quotes are all doubled."""
    assert impl.write_csv([['"" "']]) == '""""" """\r\n'


def test_ragged_records():
    """Records with different field counts."""
    result = impl.write_csv([["a", "b", "c"], ["x"], ["1", "2"]])
    assert result == "a,b,c\r\nx\r\n1,2\r\n"


def test_example_from_ticket():
    """Test the example provided in the ticket."""
    result = impl.write_csv([["2", "Portland, OR", ""], []])
    assert result == '2,"Portland, OR",\r\n\r\n'


def test_type_error_int():
    """Integer field raises TypeError with 'int' in message."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[1]])
    assert "int" in str(exc_info.value)


def test_type_error_bool():
    """Boolean field raises TypeError with 'bool' in message."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[True]])
    assert "bool" in str(exc_info.value)


def test_type_error_none():
    """None field raises TypeError with 'NoneType' in message."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[None]])
    assert "NoneType" in str(exc_info.value)


def test_type_error_bytes():
    """Bytes field raises TypeError with 'bytes' in message."""
    with pytest.raises(TypeError) as exc_info:
        impl.write_csv([[b"bytes"]])
    assert "bytes" in str(exc_info.value)
