def page(rows: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    """
    Keyset pagination for activity feed.
    
    Returns a page of rows ordered by (created_at desc, id desc) and the cursor
    for the next page, or None if this page exhausted the feed.
    """
    # Validate limit
    if not isinstance(limit, int) or limit < 1:
        raise ValueError(f"limit must be an int >= 1, got {limit!r}")
    
    # Validate and parse cursor
    c_created_at = None
    c_id = None
    if cursor is not None:
        if not isinstance(cursor, str):
            raise ValueError(f"cursor must be a str or None, got {type(cursor).__name__}")
        
        # Parse cursor format: "<created_at>:<id>"
        parts = cursor.split(':')
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"cursor is malformed: {cursor!r}")
        
        # Check that both parts are non-empty digit strings
        if not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(f"cursor is malformed: {cursor!r}")
        
        c_created_at = int(parts[0])
        c_id = int(parts[1])
    
    # Sort rows by created_at desc, then id desc
    sorted_rows = sorted(
        rows,
        key=lambda r: (r['created_at'], r['id']),
        reverse=True
    )
    
    # Filter rows strictly after the cursor position
    if cursor is not None:
        # Keep rows where:
        # - created_at < c_created_at, OR
        # - created_at == c_created_at AND id < c_id
        filtered_rows = [
            r for r in sorted_rows
            if r['created_at'] < c_created_at or (r['created_at'] == c_created_at and r['id'] < c_id)
        ]
    else:
        filtered_rows = sorted_rows
    
    # Take the first `limit` rows
    page_rows = filtered_rows[:limit]
    
    # Determine next_cursor
    if len(filtered_rows) <= limit:
        # We've exhausted candidates
        next_cursor = None
    else:
        # There are more rows, so create cursor from last row of page
        last_row = page_rows[-1]
        next_cursor = f"{last_row['created_at']}:{last_row['id']}"
    
    return (page_rows, next_cursor)
