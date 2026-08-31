def page(rows: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    """
    Perform keyset pagination on an activity feed.
    
    Args:
        rows: List of row dictionaries, each with 'id' (positive int) and 'created_at' (non-negative int)
        cursor: Position cursor as "created_at:id" or None for first page
        limit: Number of rows to return (must be positive int)
    
    Returns:
        Tuple of (page_rows, next_cursor) where next_cursor is None if page is exhausted
    
    Raises:
        ValueError: If limit is invalid or cursor is malformed
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
        
        # Parse: format must be digits:digits
        parts = cursor.split(':')
        if len(parts) != 2 or not parts[0] or not parts[1] or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError("malformed cursor")
        
        cursor_created_at = int(parts[0])
        cursor_id = int(parts[1])
    
    # Sort rows: created_at desc, id desc (newest first)
    sorted_rows = sorted(rows, key=lambda r: (-r['created_at'], -r['id']))
    
    # Filter candidates based on cursor (keep rows strictly after the cursor position)
    if cursor_created_at is not None:
        candidates = [
            r for r in sorted_rows
            if r['created_at'] < cursor_created_at or 
               (r['created_at'] == cursor_created_at and r['id'] < cursor_id)
        ]
    else:
        candidates = sorted_rows
    
    # Get page
    if len(candidates) <= limit:
        page_rows = candidates
        next_cursor = None
    else:
        page_rows = candidates[:limit]
        last_row = page_rows[-1]
        next_cursor = f"{last_row['created_at']}:{last_row['id']}"
    
    return (page_rows, next_cursor)
