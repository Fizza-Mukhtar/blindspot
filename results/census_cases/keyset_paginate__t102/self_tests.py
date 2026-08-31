import impl
import pytest


class TestPageNormal:
    """Normal path and edge case tests for keyset pagination."""
    
    def test_first_page_multiple_rows(self):
        """First page with multiple rows returns correct page and cursor."""
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
        assert page_rows[0]["created_at"] == 300
        assert page_rows[1]["id"] == 9
        assert page_rows[1]["created_at"] == 200
        assert next_cursor == "200:9"
    
    def test_second_page(self):
        """Second page with cursor returns correct rows."""
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
    
    def test_final_page(self):
        """Final page exhausts candidates and returns None cursor."""
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
    
    def test_empty_rows(self):
        """Empty rows list returns empty page and None cursor."""
        page_rows, next_cursor = impl.page([], None, 10)
        assert page_rows == []
        assert next_cursor is None
    
    def test_single_row(self):
        """Single row returns that row and None cursor."""
        rows = [{"id": 1, "created_at": 100}]
        page_rows, next_cursor = impl.page(rows, None, 10)
        assert len(page_rows) == 1
        assert page_rows[0]["id"] == 1
        assert next_cursor is None
    
    def test_limit_larger_than_candidates(self):
        """Limit larger than candidates returns all rows and None."""
        rows = [
            {"id": 2, "created_at": 200},
            {"id": 1, "created_at": 100},
        ]
        page_rows, next_cursor = impl.page(rows, None, 100)
        assert len(page_rows) == 2
        assert page_rows[0]["id"] == 2
        assert page_rows[1]["id"] == 1
        assert next_cursor is None
    
    def test_rows_with_same_timestamp(self):
        """Rows with same created_at are ordered by id (DESC)."""
        rows = [
            {"id": 2, "created_at": 100},
            {"id": 7, "created_at": 100},
            {"id": 5, "created_at": 100},
        ]
        page_rows, next_cursor = impl.page(rows, None, 10)
        assert len(page_rows) == 3
        assert page_rows[0]["id"] == 7
        assert page_rows[1]["id"] == 5
        assert page_rows[2]["id"] == 2
    
    def test_unsorted_input(self):
        """Unsorted input rows are sorted correctly."""
        rows = [
            {"id": 5, "created_at": 100},
            {"id": 4, "created_at": 300},
            {"id": 2, "created_at": 200},
            {"id": 9, "created_at": 200},
            {"id": 7, "created_at": 200},
        ]
        page_rows, next_cursor = impl.page(rows, None, 2)
        assert page_rows[0]["id"] == 4
        assert page_rows[1]["id"] == 9
        assert next_cursor == "200:9"
    
    def test_rows_with_payload(self):
        """Extra payload fields are preserved."""
        rows = [
            {"id": 1, "created_at": 100, "message": "hello", "user_id": 42},
        ]
        page_rows, next_cursor = impl.page(rows, None, 10)
        assert len(page_rows) == 1
        assert page_rows[0]["message"] == "hello"
        assert page_rows[0]["user_id"] == 42
    
    def test_cursor_pointing_to_deleted_row(self):
        """Cursor can point to a row that no longer exists."""
        rows = [
            {"id": 5, "created_at": 100},
        ]
        # Cursor points to (200, 9) which doesn't exist in rows
        page_rows, next_cursor = impl.page(rows, "200:9", 10)
        assert len(page_rows) == 1
        assert page_rows[0]["id"] == 5
        assert next_cursor is None


class TestPageErrors:
    """Error handling tests."""
    
    def test_limit_not_int(self):
        """Non-int limit raises ValueError."""
        rows = [{"id": 1, "created_at": 100}]
        with pytest.raises(ValueError):
            impl.page(rows, None, 1.5)
    
    def test_limit_zero(self):
        """Limit of 0 raises ValueError."""
        rows = [{"id": 1, "created_at": 100}]
        with pytest.raises(ValueError):
            impl.page(rows, None, 0)
    
    def test_limit_negative(self):
        """Negative limit raises ValueError."""
        rows = [{"id": 1, "created_at": 100}]
        with pytest.raises(ValueError):
            impl.page(rows, None, -1)
    
    def test_cursor_not_string(self):
        """Non-string, non-None cursor raises ValueError."""
        rows = [{"id": 1, "created_at": 100}]
        with pytest.raises(ValueError):
            impl.page(rows, 123, 10)
    
    def test_cursor_colon_issues(self):
        """Cursor without exactly one colon raises ValueError."""
        rows = [{"id": 1, "created_at": 100}]
        with pytest.raises(ValueError):
            impl.page(rows, "12", 10)
        with pytest.raises(ValueError):
            impl.page(rows, "123:456:789", 10)
    
    def test_cursor_empty_parts(self):
        """Cursor with empty parts raises ValueError."""
        rows = [{"id": 1, "created_at": 100}]
        with pytest.raises(ValueError):
            impl.page(rows, ":3", 10)
        with pytest.raises(ValueError):
            impl.page(rows, "123:", 10)
    
    def test_cursor_malformed_digits(self):
        """Cursor with non-digit characters raises ValueError."""
        rows = [{"id": 1, "created_at": 100}]
        with pytest.raises(ValueError):
            impl.page(rows, "12a:34", 10)
        with pytest.raises(ValueError):
            impl.page(rows, "123:4b", 10)
    
    def test_cursor_negative_number(self):
        """Cursor with negative numbers raises ValueError."""
        rows = [{"id": 1, "created_at": 100}]
        with pytest.raises(ValueError):
            impl.page(rows, "-1:5", 10)
        with pytest.raises(ValueError):
            impl.page(rows, "1:-5", 10)
