# DATAX-238 — Emit strict RFC 4180 CSV from an in-memory table

**Component:** `dataxport/csvwriter`
**Reporter:** Marcus (Data Platform)
**Consumers:** the nightly customer export, the audit-log dump, the billing reconciliation feed

## Background

Three of our export jobs each grew their own hand-rolled CSV writer and all
three are subtly different. The billing feed strips leading spaces off account
references, so `"  0041"` and `"0041"` collapse into the same key downstream.
The audit dump escapes an embedded double quote with a backslash, which our
partner's loader reads as a literal backslash followed by an unbalanced quote,
and the whole record shifts by one column. The customer export quotes every
field unconditionally, which is legal but bloats a 400 MB file by a third and
means a diff between two nights is unreadable.

We are replacing all three with one writer that follows RFC 4180 section 2
exactly (<https://datatracker.ietf.org/doc/html/rfc4180#section-2>), including
its ABNF grammar. The partner loaders are strict, so "close enough" is not
good enough.

## What to build

```python
def write_csv(rows: list[list[str]]) -> str:
    ...
```

`rows` is the table: a list of records, each record a list of field values.
Return the whole document as a single `str`. The function is pure and must not
mutate `rows` or any record in it.

## Record separation

Per clause 1 of section 2, records are delimited by a **CRLF** line break —
the two characters `"\r\n"`, never a bare `"\n"` and never the host platform's
native line ending.

Clause 2 of the RFC says the last record in a file *may or may not* have an
ending line break. That choice is ours to make, and we are making it here:
**every record is terminated by CRLF, including the final one.** The output
therefore always ends with `"\r\n"` unless it is empty. Our partners
concatenate our shards, and a missing terminator on shard *n* would weld its
last record onto the first record of shard *n+1*.

If `rows` is empty, return the empty string `""`.

## Field separation

Per clause 4, fields within a record are separated by a single comma and the
last field of a record is **not** followed by a comma. A record with a single
field is written as just that field.

## When to quote

Clause 5 says a field may or may not be enclosed in double quotes, and clause 6
says fields containing a line break, a double quote, or a comma should be
enclosed. We resolve the "may or may not" to the minimal form:

> A field is enclosed in double quotes **if and only if** it contains at least
> one of: a comma `,`, a double quote `"`, a carriage return `\r`, or a line
> feed `\n`. No other character, and no other property of the field, causes it
> to be quoted.

A few consequences worth spelling out, because this is exactly where the three
existing writers diverge:

- **Spaces are ordinary data.** Clause 4 says spaces are part of a field and
  are not to be ignored. A leading space, a trailing space, a run of interior
  spaces, or a field that is nothing but spaces is written through **verbatim
  and unquoted**. Nothing is trimmed, ever. `"  0041"` stays `  0041`.
- **A tab, a semicolon, a `#`, a non-ASCII character** — none of these are in
  the quote-triggering set. They are written through unquoted.
- A double quote anywhere in the field triggers quoting, not only one at the
  start. `a"b` is a quoted field.
- A **lone** `\r` with no `\n` after it, or a **lone** `\n`, triggers quoting
  just as a full CRLF does. The RFC's `TEXTDATA` production admits neither
  character, so a field containing either cannot be written unquoted; only the
  `escaped` production may hold `CR` or `LF`. The character is preserved
  exactly as given — a lone `\n` is **not** normalised into `\r\n`.

## How to quote

Wrap the field in one `"` on each side, and per clause 7 escape every double
quote that occurs inside the field by **doubling it** — writing `""` where the
data had `"`. A backslash is never an escape character in CSV; it is ordinary
data. So the field `He said "hi"` is written as:

```
"He said ""hi"""
```

and the field consisting of a single double quote is written as `""""` (an
opening quote, the doubled pair, a closing quote).

## Empty fields and empty records

An empty field is written as **nothing at all** — zero characters — not as
`""`. The RFC's `non-escaped` production is `*TEXTDATA`, which permits zero
characters, and an empty field contains none of the quote triggers above, so
the "if and only if" rule leaves it unquoted. A record of three empty fields is
written as `,,` followed by the CRLF.

A record with **zero** fields writes just its CRLF and nothing else, i.e. an
empty line. On the wire this is indistinguishable from a record holding one
empty field; that is accepted and expected. (The RFC's `record` production
requires at least one field, so it does not settle the question — this is our
decision, and the writer does not reject a zero-field record.)

## Ragged records

Clause 4 says each line *should* contain the same number of fields throughout
the file. **This writer does not enforce that.** Records of differing lengths
are written exactly as given, each with its own field count. Producing a
rectangular table is the caller's job; several of our exports deliberately emit
a short trailer record and we are not going to break them.

## Errors

Every field value must be a `str`. If any field is not — an `int`, `None`,
`bytes`, a `bool`, anything — raise `TypeError`. There is no implicit
stringification: silently calling `str()` on an `int` is how the billing feed
started emitting `True` in a boolean column. The exception message must name
the offending Python type (for example, the text `int` must appear in the
message for an integer field).

## Worked example

```python
write_csv([
    ["id", "comment", "owner"],
    ["1", 'She said "ship it"', "priya"],
    ["2", "Portland, OR", ""],
    ["3", "  keep  my  spaces  ", "dana"],
    [],
])
```

returns exactly this string (shown with the escapes visible):

```
'id,comment,owner\r\n'
'1,"She said ""ship it""",priya\r\n'
'2,"Portland, OR",\r\n'
'3,  keep  my  spaces  ,dana\r\n'
'\r\n'
```

Note row 3: the field is padded with spaces on both sides and is still
unquoted, and row 2's trailing empty field contributes nothing after its comma.

## Out of scope

- Reading or parsing CSV. This ticket is the writer only.
- Byte encoding, byte-order marks, and file I/O. We return a `str`; the caller
  encodes it.
- Dialect options — a configurable delimiter, `\n`-only line endings, an
  always-quote mode. If we need them later they arrive as a separate ticket.
- Inserting or inferring a header row. If the caller wants a header it passes
  one as the first record.
- Streaming or chunked output. The whole table is in memory already.
