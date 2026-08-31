def write_csv(rows: list[list[str]]) -> str:
    """Emit strict RFC 4180 CSV from an in-memory table."""
    if not rows:
        return ""
    
    # Validate: check that all fields are strings
    for row in rows:
        for field in row:
            if not isinstance(field, str):
                raise TypeError(f"Expected str, got {type(field).__name__}")
    
    # Main pass: generate CSV
    result = []
    for row in rows:
        fields = []
        for field in row:
            # Check if field needs quoting (contains: comma, quote, CR, or LF)
            needs_quoting = any(c in field for c in ',"\r\n')
            
            if needs_quoting:
                # Double any interior quotes and wrap in quotes
                escaped_field = field.replace('"', '""')
                fields.append('"' + escaped_field + '"')
            else:
                fields.append(field)
        
        # Join fields with comma and add CRLF
        result.append(','.join(fields) + '\r\n')
    
    return ''.join(result)
