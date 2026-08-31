import impl
import pytest

def test_first_page_no_cursor():
    """First page without cursor returns rows sorted newest first."""
    rows = [
        {"id": 4, "created_at": 300},
        {"id": 9, "created_at": 200},
        {"id": 7, "created_at": 200},
        {"id": 2, "created_at": 200},
        {"id": 5, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, None, 2)
    assert len(page_rows) == 2
    assert page_rows[0]["id"] == 4
    assert page_rows[1]["id"] == 9
    assert next_cursor == "200:9"

def test_second_page_with_cursor():
    """Second page with cursor continues from position."""
    rows = [
        {"id": 4, "created_at": 300},
        {"id": 9, "created_at": 200},
        {"id": 7, "created_at": 200},
        {"id": 2, "created_at": 200},
        {"id": 5, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, "200:9", 2)
    assert len(page_rows) == 2
    assert page_rows[0]["id"] == 7
    assert page_rows[1]["id"] == 2
    assert next_cursor == "200:2"

def test_final_page_exhausts_candidates():
    """Final page returns None as next_cursor."""
    rows = [
        {"id": 4, "created_at": 300},
        {"id": 9, "created_at": 200},
        {"id": 7, "created_at": 200},
        {"id": 2, "created_at": 200},
        {"id": 5, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, "200:2", 2)
    assert len(page_rows) == 1
    assert page_rows[0]["id"] == 5
    assert next_cursor is None

def test_empty_rows():
    """Empty rows list returns empty page."""
    page_rows, next_cursor = impl.page([], None, 10)
    assert page_rows == []
    assert next_cursor is None

def test_single_row():
    """Single row returns with no next cursor."""
    rows = [{"id": 1, "created_at": 100}]
    page_rows, next_cursor = impl.page(rows, None, 10)
    assert page_rows == rows
    assert next_cursor is None

def test_limit_of_one():
    """Limit of 1 returns single row."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 1, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, None, 1)
    assert len(page_rows) == 1
    assert page_rows[0]["id"] == 2
    assert next_cursor == "200:2"

def test_limit_larger_than_candidates():
    """Limit larger than candidates returns all with no next cursor."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 1, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, None, 100)
    assert len(page_rows) == 2
    assert next_cursor is None

def test_rows_with_same_timestamp_use_id_tiebreaker():
    """Rows with same created_at are ordered by id descending."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 3, "created_at": 100},
        {"id": 2, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, None, 3)
    assert [r["id"] for r in page_rows] == [3, 2, 1]
    assert next_cursor is None

def test_cursor_filters_by_id_within_same_timestamp():
    """Cursor correctly filters when created_at is the same."""
    rows = [
        {"id": 5, "created_at": 100},
        {"id": 3, "created_at": 100},
        {"id": 1, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, "100:3", 10)
    assert [r["id"] for r in page_rows] == [1]
    assert next_cursor is None

def test_extra_keys_in_rows_preserved():
    """Extra payload keys in rows are preserved in output."""
    rows = [
        {"id": 1, "created_at": 100, "message": "hello", "user_id": 42},
    ]
    page_rows, next_cursor = impl.page(rows, None, 10)
    assert page_rows[0]["message"] == "hello"
    assert page_rows[0]["user_id"] == 42

def test_input_rows_not_mutated():
    """Original rows list is not modified by pagination."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 1, "created_at": 100},
    ]
    rows_copy = [r.copy() for r in rows]
    impl.page(rows, None, 10)
    assert rows == rows_copy

def test_limit_must_be_positive_int():
    """Raises ValueError for non-positive or non-int limit."""
    rows = [{"id": 1, "created_at": 100}]
    with pytest.raises(ValueError):
        impl.page(rows, None, 1.5)
    with pytest.raises(ValueError):
        impl.page(rows, None, 0)
    with pytest.raises(ValueError):
        impl.page(rows, None, -1)
    with pytest.raises(ValueError):
        impl.page(rows, None, "1")

def test_cursor_must_be_string_or_none():
    """Raises ValueError if cursor is not str or None."""
    rows = [{"id": 1, "created_at": 100}]
    with pytest.raises(ValueError):
        impl.page(rows, 123, 10)
    with pytest.raises(ValueError):
        impl.page(rows, [], 10)

def test_cursor_must_have_exactly_one_colon():
    """Raises ValueError if cursor format is wrong."""
    rows = [{"id": 1, "created_at": 100}]
    with pytest.raises(ValueError):
        impl.page(rows, "100100", 10)
    with pytest.raises(ValueError):
        impl.page(rows, "100:50:25", 10)

def test_cursor_parts_must_be_nonempty_digits():
    """Raises ValueError if cursor has empty or non-digit parts."""
    rows = [{"id": 1, "created_at": 100}]
    with pytest.raises(ValueError):
        impl.page(rows, ":100", 10)
    with pytest.raises(ValueError):
        impl.page(rows, "100:", 10)
    with pytest.raises(ValueError):
        impl.page(rows, "abc:100", 10)
    with pytest.raises(ValueError):
        impl.page(rows, "-1:100", 10)

def test_cursor_past_end_returns_empty():
    """Cursor already past end returns empty page."""
    rows = [
        {"id": 2, "created_at": 200},
        {"id": 1, "created_at": 100},
    ]
    page_rows, next_cursor = impl.page(rows, "100:1", 10)
    assert page_rows == []
    assert next_cursor is None

def test_cursor_for_deleted_row_continues_from_position():
    """Cursor pointing to deleted row paging continues from that position."""
    rows = [
        {"id": 4, "created_at": 300},
        {"id": 2, "created_at": 100},
    ]
    # Cursor (200:5) is between rows; should return rows < (200:5)
    page_rows, next_cursor = impl.page(rows, "200:5", 10)
    assert len(page_rows) == 1
    assert page_rows[0]["id"] == 2
    assert next_cursor is None

def test_zero_created_at():
    """Rows with created_at == 0 are handled correctly."""
    rows = [
        {"id": 2, "created_at": 100},
        {"id": 1, "created_at": 0},
    ]
    page_rows, next_cursor = impl.page(rows, None, 10)
    assert [r["id"] for r in page_rows] == [2, 1]
    assert next_cursor is None

def test_full_feed_pagination():
    """Complete pagination through a multi-row feed."""
    rows = [
        {"id": 1, "created_at": 100},
        {"id": 5, "created_at": 500},
        {"id": 3, "created_at": 300},
        {"id": 2, "created_at": 200},
        {"id": 4, "created_at": 400},
    ]
    # Page 1
    page1, cursor1 = impl.page(rows, None, 2)
    assert [r["id"] for r in page1] == [5, 4]
    assert cursor1 == "400:4"
    
    # Page 2
    page2, cursor2 = impl.page(rows, cursor1, 2)
    assert [r["id"] for r in page2] == [3, 2]
    assert cursor2 == "200:2"
    
    # Page 3
    page3, cursor3 = impl.page(rows, cursor2, 2)
    assert [r["id"] for r in page3] == [1]
    assert cursor3 is None
