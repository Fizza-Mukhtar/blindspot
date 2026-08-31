import pytest
import impl


def test_first_page_no_cursor():
    """Test getting first page with no cursor."""
    rows = [
        {'id': 1, 'created_at': 100},
        {'id': 2, 'created_at': 200},
        {'id': 3, 'created_at': 300},
    ]
    page_rows, next_cursor = impl.page(rows, None, 2)
    assert len(page_rows) == 2
    assert page_rows[0]['id'] == 3
    assert page_rows[1]['id'] == 2
    assert next_cursor == "200:2"


def test_pagination_chain():
    """Test chaining multiple pages together."""
    rows = [
        {'id': 1, 'created_at': 100},
        {'id': 2, 'created_at': 200},
        {'id': 3, 'created_at': 300},
    ]
    page_rows, next_cursor = impl.page(rows, None, 2)
    assert [r['id'] for r in page_rows] == [3, 2]
    
    page_rows, next_cursor = impl.page(rows, next_cursor, 2)
    assert [r['id'] for r in page_rows] == [1]
    assert next_cursor is None


def test_example_from_ticket():
    """Test the exact example from the ticket specification."""
    rows = [
        {'id': 4, 'created_at': 300},
        {'id': 9, 'created_at': 200},
        {'id': 7, 'created_at': 200},
        {'id': 2, 'created_at': 200},
        {'id': 5, 'created_at': 100},
    ]
    
    page_rows, cursor = impl.page(rows, None, 2)
    assert [r['id'] for r in page_rows] == [4, 9]
    assert cursor == "200:9"
    
    page_rows, cursor = impl.page(rows, cursor, 2)
    assert [r['id'] for r in page_rows] == [7, 2]
    assert cursor == "200:2"
    
    page_rows, cursor = impl.page(rows, cursor, 2)
    assert [r['id'] for r in page_rows] == [5]
    assert cursor is None


def test_empty_rows():
    """Test pagination with empty rows."""
    page_rows, next_cursor = impl.page([], None, 10)
    assert page_rows == []
    assert next_cursor is None


def test_single_row():
    """Test pagination with a single row."""
    rows = [{'id': 1, 'created_at': 100}]
    page_rows, next_cursor = impl.page(rows, None, 10)
    assert len(page_rows) == 1
    assert page_rows[0]['id'] == 1
    assert next_cursor is None


def test_limit_equals_row_count():
    """Test when limit equals the number of rows."""
    rows = [
        {'id': 1, 'created_at': 100},
        {'id': 2, 'created_at': 200},
        {'id': 3, 'created_at': 300},
    ]
    page_rows, next_cursor = impl.page(rows, None, 3)
    assert len(page_rows) == 3
    assert next_cursor is None


def test_same_timestamp_tiebreak():
    """Test rows with same created_at use id as tie-breaker."""
    rows = [
        {'id': 1, 'created_at': 100},
        {'id': 5, 'created_at': 100},
        {'id': 3, 'created_at': 100},
    ]
    page_rows, _ = impl.page(rows, None, 10)
    assert [r['id'] for r in page_rows] == [5, 3, 1]


def test_cursor_position_semantics():
    """Test cursor points to position, not specific row (deleted row case)."""
    rows1 = [
        {'id': 1, 'created_at': 100},
        {'id': 2, 'created_at': 200},
        {'id': 3, 'created_at': 300},
    ]
    _, cursor = impl.page(rows1, None, 2)
    
    rows2 = [
        {'id': 1, 'created_at': 100},
        {'id': 3, 'created_at': 300},
    ]
    page_rows, _ = impl.page(rows2, cursor, 10)
    assert [r['id'] for r in page_rows] == [1]


def test_payload_fields_preserved():
    """Test that extra fields in rows are preserved."""
    rows = [
        {'id': 1, 'created_at': 100, 'name': 'Alice', 'data': {'x': 1}},
        {'id': 2, 'created_at': 200, 'name': 'Bob', 'data': {'y': 2}},
    ]
    page_rows, _ = impl.page(rows, None, 10)
    assert page_rows[0]['name'] == 'Bob'
    assert page_rows[0]['data'] == {'y': 2}
    assert page_rows[1]['name'] == 'Alice'


def test_unsorted_input_is_sorted():
    """Test that unsorted input is properly sorted."""
    rows = [
        {'id': 3, 'created_at': 100},
        {'id': 1, 'created_at': 300},
        {'id': 2, 'created_at': 200},
    ]
    page_rows, _ = impl.page(rows, None, 10)
    assert [r['id'] for r in page_rows] == [1, 2, 3]


def test_input_not_mutated():
    """Test that the input rows list is not mutated."""
    rows = [
        {'id': 3, 'created_at': 100},
        {'id': 1, 'created_at': 300},
        {'id': 2, 'created_at': 200},
    ]
    original = [dict(r) for r in rows]
    impl.page(rows, None, 10)
    assert rows == original


def test_limit_validation():
    """Test that invalid limit raises ValueError."""
    rows = [{'id': 1, 'created_at': 100}]
    
    with pytest.raises(ValueError, match="limit must be an int of at least 1"):
        impl.page(rows, None, 0)
    
    with pytest.raises(ValueError, match="limit must be an int of at least 1"):
        impl.page(rows, None, -1)
    
    with pytest.raises(ValueError, match="limit must be an int"):
        impl.page(rows, None, 1.5)
    
    with pytest.raises(ValueError, match="limit must be an int"):
        impl.page(rows, None, "1")


def test_cursor_type_validation():
    """Test that non-string cursor (except None) raises ValueError."""
    rows = [{'id': 1, 'created_at': 100}]
    
    with pytest.raises(ValueError, match="cursor must be a string"):
        impl.page(rows, 123, 10)
    
    with pytest.raises(ValueError, match="cursor must be a string"):
        impl.page(rows, [1, 2], 10)


def test_cursor_format_validation():
    """Test that malformed cursor format raises ValueError."""
    rows = [{'id': 1, 'created_at': 100}]
    
    with pytest.raises(ValueError, match="malformed cursor"):
        impl.page(rows, "100", 10)
    
    with pytest.raises(ValueError, match="malformed cursor"):
        impl.page(rows, "100:1:2", 10)
    
    with pytest.raises(ValueError, match="malformed cursor"):
        impl.page(rows, ":1", 10)
    
    with pytest.raises(ValueError, match="malformed cursor"):
        impl.page(rows, "100:", 10)
    
    with pytest.raises(ValueError, match="malformed cursor"):
        impl.page(rows, "100:abc", 10)


def test_cursor_negative_values():
    """Test that cursor with negative values raises ValueError."""
    rows = [{'id': 1, 'created_at': 100}]
    
    with pytest.raises(ValueError, match="malformed cursor"):
        impl.page(rows, "-100:1", 10)
    
    with pytest.raises(ValueError, match="malformed cursor"):
        impl.page(rows, "100:-1", 10)


def test_limit_one():
    """Test pagination with limit of 1."""
    rows = [
        {'id': 1, 'created_at': 100},
        {'id': 2, 'created_at': 200},
    ]
    page_rows, next_cursor = impl.page(rows, None, 1)
    assert len(page_rows) == 1
    assert page_rows[0]['id'] == 2
    assert next_cursor == "200:2"


def test_large_timestamps_and_ids():
    """Test with large timestamp and id values."""
    rows = [
        {'id': 1000000000, 'created_at': 2000000000},
        {'id': 999999999, 'created_at': 1999999999},
    ]
    page_rows, next_cursor = impl.page(rows, None, 1)
    assert page_rows[0]['id'] == 1000000000
    assert next_cursor == "2000000000:1000000000"
