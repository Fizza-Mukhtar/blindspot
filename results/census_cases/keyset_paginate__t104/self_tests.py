import impl
import pytest


def test_normal_pagination_example():
    """Test the example from the ticket."""
    rows = [
        {"id": 4, "created_at": 300},
        {"id": 9, "created_at": 200},
        {"id": 7, "created_at": 200},
        {"id": 2, "created_at": 200},
        {"id": 5, "created_at": 100},
    ]
    
    # First page
    page_rows, next_cursor = impl.page(rows, None, 2)
    assert page_rows == [
        {"id": 4, "created_at": 300},
        {"id": 9, "created_at": 200},
    ]
    assert next_cursor == "200:9"
    
    # Second page
    page_rows, next_cursor = impl.page(rows, "200:9", 2)
    assert page_rows == [
        {"id": 7, "created_at": 200},
        {"id": 2, "created_at": 200},
    ]
    assert next_cursor == "200:2"
    
    # Third page
    page_rows, next_cursor = impl.page(rows, "200:2", 2)
    assert page_rows == [
        {"id": 5, "created_at": 100},
    ]
    assert next_cursor is None


def test_empty_rows():
    """Test with empty rows list."""
    page_rows, next_cursor = impl.page([], None, 10)
    assert page_rows == []
    assert next_cursor is None


def test_rows_less_than_limit():
    """Test when rows count is less than limit."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 2, "created_at": 200},
    ]
    
    page_rows, next_cursor = impl.page(rows, None, 10)
    assert len(page_rows) == 2
    assert next_cursor is None


def test_rows_exactly_limit():
    """Test when rows count equals limit."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 1, "created_at": 100},
    ]
    
    page_rows, next_cursor = impl.page(rows, None, 2)
    assert len(page_rows) == 2
    assert next_cursor is None


def test_single_row():
    """Test with a single row."""
    rows = [{"id": 42, "created_at": 500}]
    
    page_rows, next_cursor = impl.page(rows, None, 1)
    assert page_rows == [{"id": 42, "created_at": 500}]
    assert next_cursor is None


def test_same_created_at_tiebreak():
    """Test that id is used as tiebreaker when created_at is same."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 5, "created_at": 100},
        {"id": 3, "created_at": 100},
    ]
    
    page_rows, next_cursor = impl.page(rows, None, 10)
    # Should be sorted by id descending when created_at is same
    assert [r["id"] for r in page_rows] == [5, 3, 1]


def test_cursor_multiple_pages_sequence():
    """Test paginating through multiple pages sequentially."""
    rows = [
        {"id": i, "created_at": 1000 - i * 10}
        for i in range(1, 21)
    ]
    
    all_rows = []
    cursor = None
    
    for _ in range(10):  # Limit iterations to prevent infinite loop
        page_rows, cursor = impl.page(rows, cursor, 2)
        all_rows.extend(page_rows)
        if cursor is None:
            break
    
    # Should have all rows in order
    assert len(all_rows) == 20
    # Check order: created_at descending, id descending
    for i in range(len(all_rows) - 1):
        curr_created = all_rows[i]["created_at"]
        next_created = all_rows[i + 1]["created_at"]
        assert (curr_created > next_created or 
                (curr_created == next_created and all_rows[i]["id"] > all_rows[i + 1]["id"]))


def test_preserve_extra_keys():
    """Test that extra keys in rows are preserved."""
    rows = [
        {"id": 1, "created_at": 100, "message": "hello", "user": "alice"},
        {"id": 2, "created_at": 200, "message": "world", "user": "bob"},
    ]
    
    page_rows, _ = impl.page(rows, None, 10)
    
    # Check all original keys are preserved
    assert page_rows[0]["message"] == "world"
    assert page_rows[0]["user"] == "bob"
    assert page_rows[1]["message"] == "hello"
    assert page_rows[1]["user"] == "alice"


def test_limit_invalid():
    """Test that invalid limit values raise ValueError."""
    rows = [{"id": 1, "created_at": 100}]
    
    # Negative limit
    with pytest.raises(ValueError, match="limit must be an int of at least 1"):
        impl.page(rows, None, -1)
    
    # Zero limit
    with pytest.raises(ValueError, match="limit must be an int of at least 1"):
        impl.page(rows, None, 0)
    
    # Float limit
    with pytest.raises(ValueError, match="limit must be an int of at least 1"):
        impl.page(rows, None, 1.5)
    
    # String limit
    with pytest.raises(ValueError, match="limit must be an int of at least 1"):
        impl.page(rows, None, "10")


def test_cursor_malformed():
    """Test that malformed cursors raise ValueError."""
    rows = [{"id": 1, "created_at": 100}]
    
    # Missing colon
    with pytest.raises(ValueError):
        impl.page(rows, "100", 10)
    
    # Multiple colons
    with pytest.raises(ValueError):
        impl.page(rows, "100:5:3", 10)
    
    # Non-digit created_at
    with pytest.raises(ValueError):
        impl.page(rows, "abc:5", 10)
    
    # Non-digit id
    with pytest.raises(ValueError):
        impl.page(rows, "100:xyz", 10)
    
    # Empty created_at
    with pytest.raises(ValueError):
        impl.page(rows, ":5", 10)
    
    # Empty id
    with pytest.raises(ValueError):
        impl.page(rows, "100:", 10)


def test_cursor_invalid_type():
    """Test that non-string cursor (not None) raises ValueError."""
    rows = [{"id": 1, "created_at": 100}]
    
    with pytest.raises(ValueError, match="cursor must be a string or None"):
        impl.page(rows, 123, 10)
    
    with pytest.raises(ValueError, match="cursor must be a string or None"):
        impl.page(rows, ["100", "5"], 10)


def test_cursor_logic_strictly_after():
    """Test cursor logic strictly after position."""
    rows = [
        {"id": 10, "created_at": 500},
        {"id": 9, "created_at": 400},
        {"id": 8, "created_at": 300},
        {"id": 7, "created_at": 300},
        {"id": 6, "created_at": 300},
        {"id": 5, "created_at": 200},
    ]
    
    # Cursor at (300:7) should get rows strictly after it
    page_rows, _ = impl.page(rows, "300:7", 10)
    
    # Strictly after (300:7):
    # - (300:6): created_at=300, id=6 < 7? Yes
    # - (200:5): created_at=200 < 300? Yes
    
    assert len(page_rows) == 2
    assert page_rows[0]["id"] == 6
    assert page_rows[1]["id"] == 5


def test_unordered_input():
    """Test that unordered input is sorted correctly."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 4, "created_at": 100},
        {"id": 1, "created_at": 300},
        {"id": 3, "created_at": 200},
    ]
    
    page_rows, _ = impl.page(rows, None, 10)
    
    # Should be sorted: created_at desc, then id desc
    assert [r["id"] for r in page_rows] == [1, 3, 2, 4]
    assert [r["created_at"] for r in page_rows] == [300, 200, 200, 100]


def test_cursor_row_deleted():
    """Test that paging continues correctly if cursor row was deleted."""
    rows = [
        {"id": 5, "created_at": 300},
        {"id": 1, "created_at": 100},
    ]
    
    # Cursor points to (200:3), but that row was deleted
    # Paging should continue from that position anyway
    page_rows, next_cursor = impl.page(rows, "200:3", 10)
    
    # Only (100:1) is strictly after (200:3)
    # (300:5) is newer, so it's not after
    assert page_rows == [{"id": 1, "created_at": 100}]
    assert next_cursor is None


def test_large_numbers():
    """Test with large timestamp and id values."""
    rows = [
        {"id": 9999999, "created_at": 1999999999},
        {"id": 1, "created_at": 1999999998},
    ]
    
    page_rows, next_cursor = impl.page(rows, None, 1)
    assert page_rows[0]["id"] == 9999999
    assert next_cursor == "1999999999:9999999"


def test_no_mutate_rows():
    """Test that the function doesn't mutate the input rows."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 1, "created_at": 100},
    ]
    
    rows_copy = [dict(r) for r in rows]
    impl.page(rows, None, 10)
    
    # Check rows wasn't mutated
    assert rows == rows_copy
