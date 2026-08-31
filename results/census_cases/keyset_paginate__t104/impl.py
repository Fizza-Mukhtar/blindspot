def page(rows: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    """
    Paginate a feed using keyset (seek) pagination.
    
    Args:
        rows: List of feed row dictionaries with 'id' and 'created_at' keys.
        cursor: Optional cursor string in format "<created_at>:<id>" for resuming pagination.
        limit: Maximum number of rows to return in this page (must be >= 1).
    
    Returns:
        Tuple of (page_rows, next_cursor) where next_cursor is None if page is exhausted.
    
    Raises:
        ValueError: If limit is invalid or cursor is malformed.
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
        
        # Parse cursor format: "digits:digits"
        parts = cursor.split(':')
        if len(parts) != 2:
            raise ValueError("cursor format is invalid")
        
        created_at_str, id_str = parts
        
        # Check that both parts are non-empty runs of ASCII digits
        if not created_at_str or not id_str:
            raise ValueError("cursor format is invalid")
        
        if not created_at_str.isdigit() or not id_str.isdigit():
            raise ValueError("cursor format is invalid")
        
        cursor_created_at = int(created_at_str)
        cursor_id = int(id_str)
    
    # Sort rows: newest first (created_at desc, id desc)
    sorted_rows = sorted(rows, key=lambda r: (r['created_at'], r['id']), reverse=True)
    
    # Filter rows strictly after cursor
    if cursor is None:
        candidates = sorted_rows
    else:
        candidates = [
            row for row in sorted_rows
            if (row['created_at'] < cursor_created_at or 
                (row['created_at'] == cursor_created_at and row['id'] < cursor_id))
        ]
    
    # Get first 'limit' candidates
    page_rows = candidates[:limit]
    
    # Determine next cursor
    if len(candidates) <= limit:
        # Page exhausted candidates
        next_cursor = None
    else:
        # Page has more candidates after it
        last_row = page_rows[-1]
        next_cursor = f"{last_row['created_at']}:{last_row['id']}"
    
    return (page_rows, next_cursor)
