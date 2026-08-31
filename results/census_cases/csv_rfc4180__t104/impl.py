def write_csv(rows: list[list[str]]) -> str:
    """Emit strict RFC 4180 CSV from an in-memory table."""
    if not rows:
        return ""
    
    records = []
    for row in rows:
        fields = []
        for field in row:
            if not isinstance(field, str):
                raise TypeError(f"field value must be str, not {type(field).__name__}")
            
            # Check if field needs quoting (contains comma, quote, CR, or LF)
            needs_quoting = any(c in field for c in [',', '"', '\r', '\n'])
            
            if needs_quoting:
                # Double all quotes and wrap in quotes
                escaped_field = field.replace('"', '""')
                fields.append(f'"{escaped_field}"')
            else:
                fields.append(field)
        
        # Join fields with commas and add CRLF
        record_str = ','.join(fields) + '\r\n'
        records.append(record_str)
    
    return ''.join(records)
