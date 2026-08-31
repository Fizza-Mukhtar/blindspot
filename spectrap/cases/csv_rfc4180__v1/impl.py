def write_csv(rows: list[list[str]]) -> str:
    """Serialize a table of string fields into strict RFC 4180 CSV text.

    Every record, including the last, is terminated with CRLF. A field is
    quoted if and only if it contains a comma, double quote, CR, or LF.
    Does not mutate rows. Raises TypeError if any field is not a str.
    """
    if not rows:
        return ""

    lines = []
    for record in rows:
        fields = []
        for value in record:
            if not isinstance(value, str):
                raise TypeError(
                    f"CSV field values must be str, got {type(value).__name__}"
                )
            if any(c in value for c in (',', '"', '\r', '\n')):
                fields.append('"' + value.replace('"', '""') + '"')
            else:
                fields.append(value)
        lines.append(",".join(fields))

    return "\r\n".join(lines) + "\r\n"
