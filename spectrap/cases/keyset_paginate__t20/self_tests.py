import impl
import pytest


def test_empty_rows_no_cursor():
    """Empty rows should return empty page and no cursor."""
    page_rows, next_cursor = impl.page([], None, 1)
    assert page_rows == []
    assert next_cursor is None


def test_single_row_no_cursor():
    """Single row with no cursor should return that row and no next cursor."""
    rows = [{"id": 1, "created_at": 100}]
    page_rows, next_cursor = impl.page(rows, None, 1)
    assert page_rows == rows
    assert next_cursor is None


def test_single_row_large_limit():
    """Single row with limit larger than rows should return that row and no cursor."""
    rows = [{"id": 1, "created_at": 100}]
    page_rows, next_cursor = impl.page(rows, None, 100)
    assert page_rows == rows
    assert next_cursor is None


def test_multiple_rows_sorted_by_created_at_desc():
    """Rows should be sorted by created_at descending, then id descending."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 2, "created_at": 300},
        {"id": 3, "created_at": 200},
    ]
    page_rows, next_cursor = impl.page(rows, None, 3)
    assert [r["id"] for r in page_rows] == [2, 3, 1]
    assert next_cursor is None


def test_same_created_at_sorted_by_id_desc():
    """Rows with same created_at should be sorted by id descending."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 3, "created_at": 100},
        {"id": 2, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, None, 3)
    assert [r["id"] for r in page_rows] == [3, 2, 1]
    assert next_cursor is None


def test_limit_pagination():
    """With limit < rows, should return limit rows and next cursor."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 2, "created_at": 200},
        {"id": 3, "created_at": 300},
    ]
    page_rows, next_cursor = impl.page(rows, None, 2)
    assert len(page_rows) == 2
    assert [r["id"] for r in page_rows] == [3, 2]
    assert next_cursor == "200:2"


def test_ticket_example():
    """Test the example from the ticket: (300,4) (200,9) (200,7) (200,2) (100,5)."""
    rows = [
        {"id": 4, "created_at": 300},
        {"id": 9, "created_at": 200},
        {"id": 7, "created_at": 200},
        {"id": 2, "created_at": 200},
        {"id": 5, "created_at": 100},
    ]
    
    # First page
    page_rows, next_cursor = impl.page(rows, None, 2)
    assert [r["id"] for r in page_rows] == [4, 9]
    assert next_cursor == "200:9"
    
    # Second page
    page_rows, next_cursor = impl.page(rows, "200:9", 2)
    assert [r["id"] for r in page_rows] == [7, 2]
    assert next_cursor == "200:2"
    
    # Third page
    page_rows, next_cursor = impl.page(rows, "200:2", 2)
    assert [r["id"] for r in page_rows] == [5]
    assert next_cursor is None


def test_cursor_with_nonexistent_row():
    """Cursor can point to non-existent row; paging continues from that position."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 3, "created_at": 300},
    ]
    # Cursor points to (200, 2) which does not exist
    page_rows, next_cursor = impl.page(rows, "200:2", 10)
    # Should get rows strictly after (200, 2): (100, 1)
    assert [r["id"] for r in page_rows] == [1]
    assert next_cursor is None


def test_cursor_exhausted():
    """Cursor pointing past all remaining rows should return empty."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 2, "created_at": 200},
    ]
    # Cursor at the very end
    page_rows, next_cursor = impl.page(rows, "100:1", 10)
    assert page_rows == []
    assert next_cursor is None


def test_payload_preserved():
    """Extra keys in rows should be preserved."""
    rows = [
        {"id": 1, "created_at": 100, "name": "Alice", "score": 50},
        {"id": 2, "created_at": 200, "name": "Bob", "score": 60},
    ]
    page_rows, next_cursor = impl.page(rows, None, 2)
    assert page_rows[0] == {"id": 2, "created_at": 200, "name": "Bob", "score": 60}
    assert page_rows[1] == {"id": 1, "created_at": 100, "name": "Alice", "score": 50}


def test_rows_not_mutated():
    """Original rows list should not be mutated."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 2, "created_at": 200},
    ]
    rows_copy = rows.copy()
    impl.page(rows, None, 1)
    assert rows == rows_copy


def test_invalid_limit():
    """Limit must be a positive int."""
    with pytest.raises(ValueError):
        impl.page([], None, "1")
    
    with pytest.raises(ValueError):
        impl.page([], None, 1.5)
    
    with pytest.raises(ValueError):
        impl.page([], None, 0)
    
    with pytest.raises(ValueError):
        impl.page([], None, -1)


def test_invalid_cursor_type():
    """Cursor must be str or None."""
    with pytest.raises(ValueError):
        impl.page([], 123, 1)
    
    with pytest.raises(ValueError):
        impl.page([], [1, 2], 1)


def test_malformed_cursor_format():
    """Cursor must be formatted as '<digits>:<digits>'."""
    with pytest.raises(ValueError):
        impl.page([], "123", 1)  # No colon
    
    with pytest.raises(ValueError):
        impl.page([], "1:2:3", 1)  # Multiple colons
    
    with pytest.raises(ValueError):
        impl.page([], ":123", 1)  # Empty first part
    
    with pytest.raises(ValueError):
        impl.page([], "123:", 1)  # Empty second part


def test_malformed_cursor_content():
    """Cursor parts must be non-negative digit strings."""
    with pytest.raises(ValueError):
        impl.page([], "abc:123", 1)  # Non-digit first part
    
    with pytest.raises(ValueError):
        impl.page([], "123:abc", 1)  # Non-digit second part
    
    with pytest.raises(ValueError):
        impl.page([], "-1:123", 1)  # Negative first part
    
    with pytest.raises(ValueError):
        impl.page([], "123:-1", 1)  # Negative second part
