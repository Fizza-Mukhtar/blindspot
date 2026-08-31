def page(rows: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    """
    Paginate an activity feed using keyset pagination.
    
    Args:
        rows: List of feed rows, each with at least 'id' and 'created_at' keys.
        cursor: Optional cursor string in format "<created_at>:<id>" for the next page.
        limit: Number of rows to return per page.
    
    Returns:
        A tuple of (page_rows, next_cursor) where page_rows is a list of rows
        and next_cursor is the cursor for the next page, or None if no more rows.
    
    Raises:
        ValueError: If limit is not an int >= 1, or cursor is malformed.
    """
    # Validate limit
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be an int of at least 1")
    
    # Validate and parse cursor
    cursor_created_at = None
    cursor_id = None
    if cursor is not None:
        if not isinstance(cursor, str):
            raise ValueError("cursor must be a string or None")
        
        parts = cursor.split(':')
        if len(parts) != 2:
            raise ValueError("cursor format invalid")
        
        created_at_str, id_str = parts
        
        # Both parts must be non-empty and contain only digits
        if not (created_at_str and created_at_str.isdigit() and id_str and id_str.isdigit()):
            raise ValueError("cursor format invalid")
        
        cursor_created_at = int(created_at_str)
        cursor_id = int(id_str)
    
    # Sort rows: created_at descending, id descending (newest first)
    sorted_rows = sorted(rows, key=lambda row: (-row['created_at'], -row['id']))
    
    # Filter based on cursor: keep rows strictly after the cursor position
    if cursor is not None:
        filtered_rows = [
            row for row in sorted_rows
            if row['created_at'] < cursor_created_at or 
               (row['created_at'] == cursor_created_at and row['id'] < cursor_id)
        ]
    else:
        filtered_rows = sorted_rows
    
    # Take the first `limit` rows
    page_rows = filtered_rows[:limit]
    
    # Build next_cursor: None if page exhausted the candidates
    if len(filtered_rows) > limit:
        next_cursor = f"{page_rows[-1]['created_at']}:{page_rows[-1]['id']}"
    else:
        next_cursor = None
    
    return (page_rows, next_cursor)
