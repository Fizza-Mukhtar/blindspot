def write_csv(rows: list[list[str]]) -> str:
    """Emit strict RFC 4180 CSV from an in-memory table.
    
    Args:
        rows: A list of records, each a list of field values (must be strings).
    
    Returns:
        The entire CSV document as a single string with CRLF line endings.
        Empty rows returns an empty string.
    
    Raises:
        TypeError: If any field value is not a string.
    """
    if not rows:
        return ""
    
    lines = []
    for record in rows:
        fields = []
        for field in record:
            # Type check: field must be str
            if not isinstance(field, str):
                raise TypeError(f"field must be str, not {type(field).__name__}")
            
            # RFC 4180: quote if field contains comma, double quote, CR, or LF
            needs_quoting = any(c in field for c in ',"\r\n')
            
            if needs_quoting:
                # Escape interior double quotes by doubling them (clause 7)
                escaped = field.replace('"', '""')
                fields.append(f'"{escaped}"')
            else:
                # Unquoted field as-is
                fields.append(field)
        
        # Join fields with commas and add CRLF line ending
        line = ','.join(fields) + '\r\n'
        lines.append(line)
    
    return ''.join(lines)
