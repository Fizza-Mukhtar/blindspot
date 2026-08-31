def page(rows: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    """
    Paginate activity feed rows using keyset pagination.
    
    Returns a page of rows sorted newest-first and the cursor for the next page.
    """
    # Validate limit
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be an int >= 1")
    
    # Validate and parse cursor
    cursor_created_at = None
    cursor_id = None
    if cursor is not None:
        if not isinstance(cursor, str):
            raise ValueError("cursor must be str or None")
        
        parts = cursor.split(":")
        if len(parts) != 2:
            raise ValueError("malformed cursor")
        
        if not parts[0] or not parts[1]:
            raise ValueError("malformed cursor")
        
        if not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError("malformed cursor")
        
        cursor_created_at = int(parts[0])
        cursor_id = int(parts[1])
    
    # Sort rows by (created_at DESC, id DESC)
    sorted_rows = sorted(rows, key=lambda r: (-r["created_at"], -r["id"]))
    
    # Filter by cursor
    if cursor is None:
        candidates = sorted_rows
    else:
        candidates = [
            r for r in sorted_rows
            if r["created_at"] < cursor_created_at or 
               (r["created_at"] == cursor_created_at and r["id"] < cursor_id)
        ]
    
    # Take first limit rows
    page_rows = candidates[:limit]
    
    # Determine next cursor
    if len(candidates) > limit:
        last_row = page_rows[-1]
        next_cursor = f"{last_row['created_at']}:{last_row['id']}"
    else:
        next_cursor = None
    
    return (page_rows, next_cursor)
