import pytest
import impl


def test_simple_pagination_single_page():
    """Test basic pagination when all rows fit in one page."""
    rows = [
        {"id": 1, "created_at": 100, "text": "first"},
        {"id": 2, "created_at": 200, "text": "second"},
        {"id": 3, "created_at": 150, "text": "third"},
    ]
    page_rows, next_cursor = impl.page(rows, None, 10)
    
    assert len(page_rows) == 3
    assert page_rows[0]["id"] == 2
    assert page_rows[1]["id"] == 3
    assert page_rows[2]["id"] == 1
    assert next_cursor is None


def test_pagination_with_limit():
    """Test pagination respects limit and generates correct cursor."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 2, "created_at": 200},
        {"id": 3, "created_at": 150},
    ]
    page_rows, next_cursor = impl.page(rows, None, 2)
    
    assert len(page_rows) == 2
    assert page_rows[0]["id"] == 2
    assert page_rows[1]["id"] == 3
    assert next_cursor == "150:3"


def test_pagination_multiple_pages():
    """Test example from ticket: paginate through multiple pages."""
    # Over (created_at, id) pairs (300,4) (200,9) (200,7) (200,2) (100,5)
    rows = [
        {"id": 4, "created_at": 300},
        {"id": 9, "created_at": 200},
        {"id": 7, "created_at": 200},
        {"id": 2, "created_at": 200},
        {"id": 5, "created_at": 100},
    ]
    
    # First page: [4, 9] / "200:9"
    page1, cursor1 = impl.page(rows, None, 2)
    assert len(page1) == 2
    assert page1[0]["id"] == 4
    assert page1[1]["id"] == 9
    assert cursor1 == "200:9"
    
    # Second page: [7, 2] / "200:2"
    page2, cursor2 = impl.page(rows, cursor1, 2)
    assert len(page2) == 2
    assert page2[0]["id"] == 7
    assert page2[1]["id"] == 2
    assert cursor2 == "200:2"
    
    # Third page: [5] / None
    page3, cursor3 = impl.page(rows, cursor2, 2)
    assert len(page3) == 1
    assert page3[0]["id"] == 5
    assert cursor3 is None


def test_same_timestamp_tiebreak_by_id():
    """Test that rows with same created_at are sorted by id descending."""
    rows = [
        {"id": 1, "created_at": 200},
        {"id": 3, "created_at": 200},
        {"id": 2, "created_at": 200},
    ]
    page_rows, _ = impl.page(rows, None, 10)
    
    # Should be sorted by id descending within same timestamp
    assert [r["id"] for r in page_rows] == [3, 2, 1]


def test_cursor_filtering():
    """Test cursor correctly filters rows after position."""
    rows = [
        {"id": 10, "created_at": 300},
        {"id": 9, "created_at": 200},
        {"id": 8, "created_at": 200},
        {"id": 7, "created_at": 100},
    ]
    
    # Cursor at (200, 9) should only get rows strictly after
    page_rows, _ = impl.page(rows, "200:9", 10)
    assert [r["id"] for r in page_rows] == [8, 7]


def test_empty_rows():
    """Test pagination with empty rows list."""
    page_rows, next_cursor = impl.page([], None, 10)
    assert page_rows == []
    assert next_cursor is None


def test_cursor_exhausts_rows():
    """Test cursor that exhausts all remaining rows."""
    rows = [{"id": 1, "created_at": 100}]
    page_rows, next_cursor = impl.page(rows, "100:1", 10)
    assert page_rows == []
    assert next_cursor is None


def test_limit_one():
    """Test pagination with limit of 1."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 1, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, None, 1)
    assert len(page_rows) == 1
    assert page_rows[0]["id"] == 2
    assert next_cursor == "200:2"


def test_limit_larger_than_rows():
    """Test pagination when limit is larger than available rows."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 1, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, None, 100)
    assert len(page_rows) == 2
    assert next_cursor is None


def test_preserves_payload():
    """Test that extra keys in rows are preserved untouched."""
    rows = [
        {"id": 1, "created_at": 100, "text": "hello", "user": "alice", "likes": 42},
        {"id": 2, "created_at": 200, "text": "world", "user": "bob"},
    ]
    page_rows, _ = impl.page(rows, None, 10)
    
    assert page_rows[0] == {"id": 2, "created_at": 200, "text": "world", "user": "bob"}
    assert page_rows[1] == {"id": 1, "created_at": 100, "text": "hello", "user": "alice", "likes": 42}


def test_does_not_mutate_input():
    """Test that the function does not mutate the input rows list."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 2, "created_at": 200},
    ]
    rows_copy = [dict(r) for r in rows]
    impl.page(rows, None, 10)
    
    assert rows == rows_copy


def test_limit_validation():
    """Test that invalid limit values raise ValueError."""
    rows = [{"id": 1, "created_at": 100}]
    
    # Non-integer limit
    with pytest.raises(ValueError, match="limit must be an int"):
        impl.page(rows, None, 1.5)
    
    with pytest.raises(ValueError, match="limit must be an int"):
        impl.page(rows, None, "1")
    
    # Limit < 1
    with pytest.raises(ValueError, match="limit must be an int"):
        impl.page(rows, None, 0)
    
    with pytest.raises(ValueError, match="limit must be an int"):
        impl.page(rows, None, -5)


def test_cursor_type_validation():
    """Test that cursor must be string or None."""
    rows = [{"id": 1, "created_at": 100}]
    
    with pytest.raises(ValueError, match="cursor must be a string or None"):
        impl.page(rows, 123, 10)
    
    with pytest.raises(ValueError, match="cursor must be a string or None"):
        impl.page(rows, [], 10)


def test_cursor_format_validation():
    """Test that cursor format is validated thoroughly."""
    rows = [{"id": 1, "created_at": 100}]
    
    # No colon
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, "100100", 10)
    
    # Multiple colons
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, "100:1:extra", 10)
    
    # Empty parts
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, ":100", 10)
    
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, "100:", 10)
    
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, ":", 10)
    
    # Non-digit parts
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, "abc:100", 10)
    
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, "100:xyz", 10)
    
    # Negative numbers (minus sign is not a digit)
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, "-1:100", 10)
    
    with pytest.raises(ValueError, match="cursor format invalid"):
        impl.page(rows, "100:-1", 10)


def test_large_numbers():
    """Test pagination with very large timestamps and ids."""
    rows = [
        {"id": 9999999999, "created_at": 1234567890},
        {"id": 9999999998, "created_at": 1234567890},
        {"id": 1, "created_at": 0},
    ]
    page_rows, next_cursor = impl.page(rows, None, 2)
    
    assert len(page_rows) == 2
    assert page_rows[0]["id"] == 9999999999
    assert page_rows[1]["id"] == 9999999998
    assert next_cursor == "1234567890:9999999998"


def test_edge_case_zero_timestamp():
    """Test pagination with created_at of 0 and cursor at zero."""
    rows = [
        {"id": 2, "created_at": 100},
        {"id": 1, "created_at": 0},
    ]
    page_rows, _ = impl.page(rows, None, 10)
    
    assert [r["id"] for r in page_rows] == [2, 1]
    
    # Can also paginate from position at 0
    page_rows2, _ = impl.page(rows, "0:1", 10)
    assert page_rows2 == []
