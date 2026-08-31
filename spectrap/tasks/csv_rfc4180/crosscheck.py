"""Independent oracle for DATAX-238 (csv_rfc4180).

Deliberately does NOT re-implement the quoting logic by hand.  It delegates
the whole serialisation to the Python standard library's ``csv`` module --
an independent implementation of RFC 4180's writing rules -- configured so
that its dialect knobs line up one-for-one with the clauses of the RFC:

    delimiter      ','      -> COMMA (%x2C), clause 4
    quotechar      '"'      -> DQUOTE (%x22), clauses 5/6
    doublequote    True     -> clause 7 (escape DQUOTE by doubling it)
    escapechar     None     -> a backslash is ordinary data, never an escape
    lineterminator '\\r\\n'   -> CRLF, clause 1
    quoting        MINIMAL  -> the ticket's "if and only if" resolution

With ``QUOTE_MINIMAL`` CPython quotes a field exactly when it contains the
delimiter, the quotechar, or any character of the lineterminator -- i.e.
exactly ``,``, ``"``, CR or LF.  Space, TAB, ``;``, ``#``, backslash and
non-ASCII are therefore passed through unquoted and untrimmed, which is what
clause 4 ("Spaces are considered part of a field and should not be ignored")
and the ticket require.

Two things the csv module will not do for us, handled explicitly here:

  * ``csv.writer`` stringifies non-``str`` values instead of rejecting them,
    so the type check happens before anything reaches the module.
  * CPython has one documented special case that is *not* in RFC 4180: a
    record consisting of a single empty field is emitted as ``""\\r\\n`` so a
    reader can tell it apart from a blank line.  The ticket rules the other
    way, and ``non-escaped = *TEXTDATA`` admits zero characters, so that one
    case is corrected back to a bare CRLF.

``_oracle_abnf`` is a second, structurally different implementation derived
straight from the ABNF.  ``oracle`` runs both and raises if they disagree,
so a bug in either is loud rather than silent.
"""

from __future__ import annotations

import csv
import io

ORACLE_NOTES: str = (
    "Basis: stdlib csv.writer (delimiter=',', quotechar='\"', "
    "doublequote=True, escapechar=None, lineterminator=CRLF, "
    "QUOTE_MINIMAL), one record at a time, with an explicit str type check "
    "in front and CPython's non-RFC rendering of a lone empty field as two "
    "quotes corrected to zero characters. Cross-checked on every call "
    "against a second ABNF-driven implementation (trigger set comma, "
    "DQUOTE, CR, LF). RFC 4180 s2 clauses read from datatracker: c1 CRLF "
    "record separator; c2 trailing break optional in the RFC, resolved to "
    "always-present by the ticket (file = [header CRLF] record *(CRLF "
    "record) [CRLF] permits it); c4 comma separator, 'Spaces are considered "
    "part of a field and should not be ignored', and equal field counts are "
    "only a SHOULD; c5 'may or may not be enclosed' resolved to minimal "
    "quoting; c6 trigger set; c7 an inner DQUOTE is doubled, never "
    "backslashed. ABNF: non-escaped = *TEXTDATA, so an empty field is zero "
    "characters; TEXTDATA = %x20-21/%x23-2B/%x2D-7E admits neither CR nor "
    "LF, so a lone CR or lone LF can only sit inside `escaped` and is "
    "preserved verbatim (no LF -> CRLF normalisation). "
    "Deliberate ticket-vs-RFC gaps, each stated outright in SPEC.md and so "
    "NOT defects: TEXTDATA is printable US-ASCII only, so TAB and every "
    "non-ASCII character (generators.py emits 'naive' with a diaeresis) lie "
    "outside BOTH productions -- the ticket's rule that they pass through "
    "unquoted is a deliberate superset of the ABNF, not a consequence of "
    "it; and `record = field *(COMMA field)` requires >=1 field, so the "
    "zero-field record's bare CRLF is the ticket's call, not the RFC's. "
    "Genuine under-determination (ambiguity, not defect): whether a tuple "
    "or other non-list record is accepted, and whether the TypeError "
    "message must locate the offending value beyond naming its type. This "
    "oracle accepts any sequence as a record and names only the type."
)

# The four characters that force the ``escaped`` production.  Everything
# else -- space, TAB, ';', '#', '\', non-ASCII -- is written through.
_TRIGGERS = frozenset(',"\r\n')


def _check_types(rows) -> None:
    """Reject any non-``str`` field, naming the offending Python type."""
    for row in rows:
        for value in row:
            if not isinstance(value, str):
                raise TypeError(
                    "csv field values must be str, got "
                    f"{type(value).__name__}: {value!r}"
                )


def _oracle_csv_module(rows) -> str:
    """Delegate to the stdlib ``csv`` module, one record at a time."""
    out = []
    for row in rows:
        buf = io.StringIO()
        writer = csv.writer(
            buf,
            delimiter=",",
            quotechar='"',
            doublequote=True,
            escapechar=None,
            lineterminator="\r\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writerow(list(row))
        text = buf.getvalue()
        # CPython-only special case, absent from RFC 4180: a lone empty
        # field is emitted as '""' so a reader can distinguish it from a
        # blank line.  The ticket and `non-escaped = *TEXTDATA` say zero
        # characters, so undo it.
        if len(row) == 1 and row[0] == "":
            assert text == '""\r\n', text
            text = "\r\n"
        out.append(text)
    return "".join(out)


def _oracle_abnf(rows) -> str:
    """Second implementation, taken straight from the ABNF productions."""
    lines = []
    for row in rows:
        fields = []
        for value in row:
            if any(ch in _TRIGGERS for ch in value):
                # escaped = DQUOTE *(TEXTDATA/COMMA/CR/LF/2DQUOTE) DQUOTE
                fields.append('"' + value.replace('"', '""') + '"')
            else:
                # non-escaped = *TEXTDATA  (zero characters permitted)
                fields.append(value)
        lines.append(",".join(fields))
    return "".join(line + "\r\n" for line in lines)


def oracle(rows):
    """Independent implementation of ``write_csv``."""
    _check_types(rows)
    a = _oracle_csv_module(rows)
    b = _oracle_abnf(rows)
    if a != b:  # pragma: no cover - internal consistency guard
        raise AssertionError(f"oracle internal disagreement: {a!r} != {b!r}")
    return a


# ---------------------------------------------------------------------------
# Expected values derived from RFC 4180 section 2 (its own worked examples
# where it has them) and from the ticket's explicit resolutions.
# ---------------------------------------------------------------------------

KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # Empty table -> empty document.
    (([],), {}, ""),

    # RFC s2 example for clauses 1/4:  aaa,bbb,ccc CRLF zzz,yyy,xxx CRLF
    (([["aaa", "bbb", "ccc"], ["zzz", "yyy", "xxx"]],), {},
     "aaa,bbb,ccc\r\nzzz,yyy,xxx\r\n"),

    # RFC s2 clause 6 example: a field holding a CRLF is enclosed, and the
    # CRLF survives verbatim.  Minimal quoting leaves aaa/ccc bare.
    (([["aaa", "b\r\nbb", "ccc"], ["zzz", "yyy", "xxx"]],), {},
     'aaa,"b\r\nbb",ccc\r\nzzz,yyy,xxx\r\n'),

    # RFC s2 clause 7 example:  "aaa","b""bb","ccc"
    (([["aaa", 'b"bb', "ccc"]],), {}, 'aaa,"b""bb",ccc\r\n'),

    # Clause 6: an embedded comma forces `escaped`.
    (([["Portland, OR"]],), {}, '"Portland, OR"\r\n'),

    # Clause 4: space is TEXTDATA (%x20); nothing is trimmed and nothing is
    # quoted on account of whitespace.
    (([["  keep  my  spaces  "], ["   "], ["  0041"]],), {},
     "  keep  my  spaces  \r\n   \r\n  0041\r\n"),

    # non-escaped = *TEXTDATA permits zero characters.
    (([["", "", ""]],), {}, ",,\r\n"),
    (([[""]],), {}, "\r\n"),

    # Zero-field record -> bare CRLF (the ticket's resolution).
    (([[]],), {}, "\r\n"),

    # A field that is one DQUOTE:  DQUOTE 2DQUOTE DQUOTE
    (([['"']],), {}, '""""\r\n'),

    # TEXTDATA admits neither CR nor LF, so a lone CR / lone LF must be
    # escaped, and is not normalised.
    (([["lone\rcr"], ["lone\nlf"], ["\r"], ["\n"]],), {},
     '"lone\rcr"\r\n"lone\nlf"\r\n"\r"\r\n"\n"\r\n'),

    # Outside the trigger set -> written through unquoted.
    (([["semi;colon\ttab#hash", "back\\slash"]],), {},
     "semi;colon\ttab#hash,back\\slash\r\n"),

    # Clause 4's equal-field-count rule is a SHOULD; ragged rows pass through.
    (([["a"], ["b", "c"], [], ["d", "e", "f"]],), {},
     "a\r\nb,c\r\n\r\nd,e,f\r\n"),

    # The ticket's worked example, verbatim.
    (([
        ["id", "comment", "owner"],
        ["1", 'She said "ship it"', "priya"],
        ["2", "Portland, OR", ""],
        ["3", "  keep  my  spaces  ", "dana"],
        [],
    ],), {},
     'id,comment,owner\r\n'
     '1,"She said ""ship it""",priya\r\n'
     '2,"Portland, OR",\r\n'
     '3,  keep  my  spaces  ,dana\r\n'
     '\r\n'),

    # Every non-str field value must raise TypeError.
    (([["a", 1]],), {}, ("raises", "TypeError")),
    (([["ok"], [None]],), {}, ("raises", "TypeError")),
    (([[b"bytes"]],), {}, ("raises", "TypeError")),
    (([[True]],), {}, ("raises", "TypeError")),
]
