def page(rows: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    """
    Keyset pagination for an activity feed.
    
    Returns a page of rows ordered newest-first, with a cursor for the next page.
    Raises ValueError if limit is invalid or cursor is malformed.
    """
    # Validate limit
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be an int of at least 1")
    
    # Validate and parse cursor
    c_created_at = None
    c_id = None
    if cursor is not None:
        if not isinstance(cursor, str):
            raise ValueError("malformed cursor")
        parts = cursor.split(':')
        if len(parts) != 2:
            raise ValueError("malformed cursor")
        if not parts[0] or not parts[1]:
            raise ValueError("malformed cursor")
        if not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError("malformed cursor")
        c_created_at = int(parts[0])
        c_id = int(parts[1])
    
    # Sort rows by created_at (DESC) then id (DESC)
    sorted_rows = sorted(rows, key=lambda r: (r['created_at'], r['id']), reverse=True)
    
    # Filter based on cursor if provided
    candidates = sorted_rows
    if cursor is not None:
        filtered = []
        for row in candidates:
            if row['created_at'] < c_created_at or (row['created_at'] == c_created_at and row['id'] < c_id):
                filtered.append(row)
        candidates = filtered
    
    # Get the first limit rows
    page_rows = candidates[:limit]
    
    # Determine next cursor
    next_cursor = None
    if len(candidates) > limit:
        last_row = page_rows[-1]
        next_cursor = f"{last_row['created_at']}:{last_row['id']}"
    
    return (page_rows, next_cursor)
