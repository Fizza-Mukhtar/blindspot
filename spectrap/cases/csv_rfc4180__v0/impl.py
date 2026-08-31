def write_csv(rows: list[list[str]]) -> str:
    """Render an in-memory table as a strict RFC 4180 CSV document.

    Records are separated by CRLF (including after the final record), fields
    within a record by a single comma, and a field is quoted if and only if it
    contains a comma, a double quote, a carriage return, or a line feed.
    Quoted fields have internal double quotes doubled. Every field value must
    be a str; anything else raises TypeError. Returns '' for an empty table.
    Does not mutate its input.
    """
    if not rows:
        return ""

    quote_triggers = ('"', ',', '\r', '\n')
    lines = []
    for record in rows:
        encoded_fields = []
        for value in record:
            if not isinstance(value, str):
                raise TypeError(
                    f"CSV field values must be str, got {type(value).__name__!r}"
                )
            if any(trigger in value for trigger in quote_triggers):
                encoded_fields.append('"' + value.replace('"', '""') + '"')
            else:
                encoded_fields.append(value)
        lines.append(",".join(encoded_fields))

    return "".join(line + "\r\n" for line in lines)
