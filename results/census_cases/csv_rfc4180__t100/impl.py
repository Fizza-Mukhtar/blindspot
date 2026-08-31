def write_csv(rows: list[list[str]]) -> str:
    """Emit strict RFC 4180 CSV from an in-memory table."""
    if not rows:
        return ""
    
    result = []
    
    for record in rows:
        fields = []
        for field in record:
            if not isinstance(field, str):
                type_name = type(field).__name__
                raise TypeError(f"Field value must be str, not {type_name}")
            
            # Check if field needs quoting: comma, quote, CR, or LF
            needs_quoting = any(c in field for c in ',"\r\n')
            
            if needs_quoting:
                # Escape double quotes by doubling them
                escaped_field = field.replace('"', '""')
                # Wrap in quotes
                fields.append(f'"{escaped_field}"')
            else:
                fields.append(field)
        
        # Join fields with commas and add CRLF
        record_str = ','.join(fields) + '\r\n'
        result.append(record_str)
    
    return ''.join(result)
