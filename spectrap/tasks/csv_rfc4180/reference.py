"""Reference implementation for DATAX-238 (strict RFC 4180 CSV serialisation).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: RFC 4180 section 2, clauses 1, 2, 4, 5, 6 and 7, together with the
ABNF grammar in the same section.
https://datatracker.ietf.org/doc/html/rfc4180#section-2
"""

from __future__ import annotations

from typing import Iterable

# Clause 1: "Each record is located on a separate line, delimited by a line
# break (CRLF)."  Clause 2 leaves the terminator on the final record optional;
# DATAX-238 pins it down as always present.
CRLF = "\r\n"

DQUOTE = '"'
COMMA = ","

# The characters that force a field into the ABNF `escaped` production.
# `non-escaped = *TEXTDATA` and TEXTDATA = %x20-21 / %x23-2B / %x2D-7E, which
# admits neither DQUOTE (%x22), COMMA (%x2C), CR nor LF.  Clause 6 names the
# same set in prose.  Note that a *lone* CR or LF is excluded from TEXTDATA
# just as a full CRLF pair is, so either one on its own forces quoting.
_QUOTE_TRIGGERS = (COMMA, DQUOTE, "\r", "\n")


def _encode_field(value: str, row_index: int, field_index: int) -> str:
    """Render one field, quoting it only when the grammar requires it."""
    if not isinstance(value, str):
        # DATAX-238: no implicit stringification.  The message names the type.
        raise TypeError(
            f"CSV field must be str, got {type(value).__name__} "
            f"at row {row_index}, field {field_index}"
        )

    # Quote if and only if a trigger character is present.  Spaces, tabs,
    # semicolons and non-ASCII characters are deliberately *not* triggers, and
    # nothing is stripped from either end (clause 4: "Spaces are considered
    # part of a field and should not be ignored").
    if not any(trigger in value for trigger in _QUOTE_TRIGGERS):
        # Includes the empty field, which renders as zero characters -- never
        # as a bare pair of quotes.
        return value

    # Clause 7: a double quote inside a quoted field is escaped by preceding it
    # with another double quote.  A backslash is never an escape in CSV.
    return DQUOTE + value.replace(DQUOTE, DQUOTE * 2) + DQUOTE


def _encode_record(row: Iterable[str], row_index: int) -> str:
    """Join one record's fields with commas (clause 4: no trailing comma)."""
    fields = [
        _encode_field(value, row_index, field_index)
        for field_index, value in enumerate(row)
    ]
    # A record with zero fields joins to "", so it contributes only its CRLF.
    return COMMA.join(fields)


def write_csv(rows: list[list[str]]) -> str:
    """Serialise a table to RFC 4180 CSV text.

    Records of differing lengths are written as-is: clause 4's "each line
    should contain the same number of fields" is advisory and DATAX-238
    explicitly declines to enforce it.
    """
    out: list[str] = []
    for row_index, row in enumerate(rows):
        out.append(_encode_record(row, row_index))
        # Every record is terminated, the last one included, so an empty table
        # is the only input that yields the empty string.
        out.append(CRLF)
    return "".join(out)
