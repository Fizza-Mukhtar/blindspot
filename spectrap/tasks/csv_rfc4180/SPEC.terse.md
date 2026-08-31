# DATAX-238 — Emit strict RFC 4180 CSV from an in-memory table

**Component:** `dataxport/csvwriter`
**Reporter:** Marcus (Data Platform)

## Background

The customer export, the audit dump and the billing feed each grew their own
CSV writer and all three are subtly different — one trims account references
so `  0041` and `0041` collide downstream, one backslash-escapes embedded
quotes and shifts the partner's record by a column, one quotes every field and
adds a third to a 400 MB file. Replace all three with one writer following
RFC 4180 section 2 and its ABNF grammar exactly
(<https://datatracker.ietf.org/doc/html/rfc4180#section-2>).

## What to build

```python
def write_csv(rows: list[list[str]]) -> str:
    ...
```

`rows` is the table: a list of records, each a list of field values. Return the
whole document as one `str`. Pure — do not mutate `rows` or any record in it.
Empty `rows` returns `""`.

## Behaviour

Records are delimited per clause 1 by CRLF, the two characters `"\r\n"`, never
a bare `"\n"` and never the platform's native ending. Clause 2 leaves a
terminator on the last record optional; we are pinning it, since partners
concatenate our shards — every record ends with CRLF, the last included, so
non-empty output always ends `"\r\n"`. Fields within a record are joined by
single commas with none after the last (clause 4).

Clauses 5 and 6 leave part of the quoting to the writer; take the minimal
reading, so a field is enclosed in double quotes if and only if it contains at
least one comma, double quote, CR or LF, and nothing else about a field causes
it to be quoted. Spaces are ordinary content per clause 4, never trimmed and
never a reason to quote, so `  keep  my  spaces  ` and a field of nothing but
spaces both go out padded and bare; tabs, semicolons, `#`, backslashes and
non-ASCII are likewise not triggers. A double quote counts wherever it sits,
not just at the start. A lone `\r`, or a lone `\n`, forces quoting exactly as
a full CRLF does — `TEXTDATA` admits neither, so only `escaped` can hold one —
and is then preserved as given, so a lone `\n` is not normalised to `\r\n`.

A quoted field gets one `"` each side and every interior double quote doubled,
`""` where the data had `"` (clause 7); a backslash is never an escape
character here, and doubling is the only change made to field content, quoted
or not. So `He said "hi"` is written `"He said ""hi"""`, and a field that is
one double quote is written `""""`.

An empty field is zero characters, not `""` — `non-escaped` is `*TEXTDATA`,
which permits none, and an empty field holds no trigger — so a record of three
empty fields is `,,` plus its CRLF. A record with no fields at all writes just
its CRLF, an empty line, indistinguishable on the wire from one empty field;
that is our call, not the RFC's (its `record` production needs at least one
field), and such a record is written rather than rejected. Clause 4's equal
field count per line is advisory and we do not enforce it: ragged records go
out exactly as given, each with its own count, since some exports deliberately
emit a short trailer.

Every field value must be a `str`; anything else — `int`, `bool`, `None`,
`bytes` — raises `TypeError` rather than being stringified. The message must
name the offending Python type (for an integer field, the text `int` appears
in it).

So `write_csv([["2", "Portland, OR", ""], []])` returns
`'2,"Portland, OR",\r\n\r\n'`.

## Out of scope

Parsing CSV; encoding, BOMs and file I/O — we return a `str`; dialect options
such as a configurable delimiter, `\n`-only endings or an always-quote mode;
inferring a header row (pass one as the first record); streaming.
