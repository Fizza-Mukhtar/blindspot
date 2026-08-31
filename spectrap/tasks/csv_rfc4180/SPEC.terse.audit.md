# SPEC.terse.md determination audit — csv_rfc4180 (DATAX-238)

Every assertion in `selftest.py` checked against `SPEC.terse.md` alone, plus
RFC 4180 section 2 where the ticket cites it normatively.

| selftest function | determined by | verdict |
| --- | --- | --- |
| `test_records_are_delimited_by_crlf` | "Records are delimited per clause 1 by CRLF, the two characters `\r\n`, never a bare `\n` and never the platform's native ending." plus "every record ends with CRLF, the last included" | DETERMINED |
| `test_final_record_is_also_terminated` | "Clause 2 leaves a terminator on the last record optional; we are pinning it, since partners concatenate our shards — every record ends with CRLF, the last included, so non-empty output always ends `\r\n`." | DETERMINED |
| `test_fields_are_comma_separated_with_no_trailing_comma` | "Fields within a record are joined by single commas with none after the last (clause 4)." | DETERMINED |
| `test_field_containing_a_comma_is_quoted` | "a field is enclosed in double quotes if and only if it contains at least one comma, double quote, CR or LF" | DETERMINED |
| `test_embedded_double_quote_is_escaped_by_doubling` | "A quoted field gets one `\"` each side and every interior double quote doubled, `\"\"` where the data had `\"` (clause 7)"; the ticket spells out `He said "hi"` → `"He said ""hi"""` | DETERMINED |
| `test_double_quote_is_never_backslash_escaped` | same doubling sentence, plus "a backslash is never an escape character here, and doubling is the only change made to field content, quoted or not" | DETERMINED |
| `test_lone_double_quote_field` | "a field that is one double quote is written `\"\"\"\"`" | DETERMINED |
| `test_field_containing_crlf_is_quoted_and_preserved` | the if-and-only-if trigger set (CR and LF both present) plus "doubling is the only change made to field content, quoted or not" | DETERMINED |
| `test_lone_cr_and_lone_lf_force_quoting_and_are_not_normalised` | "A lone `\r`, or a lone `\n`, forces quoting exactly as a full CRLF does — `TEXTDATA` admits neither, so only `escaped` can hold one — and is then preserved as given, so a lone `\n` is not normalised to `\r\n`." | DETERMINED |
| `test_spaces_are_data_and_do_not_trigger_quoting` | "Spaces are ordinary content per clause 4, never trimmed and never a reason to quote, so `  keep  my  spaces  ` and a field of nothing but spaces both go out padded and bare" | DETERMINED |
| `test_field_of_only_spaces_is_written_verbatim` | same sentence — "and a field of nothing but spaces both go out padded and bare" | DETERMINED |
| `test_padding_survives_when_the_field_is_quoted_for_another_reason` | trigger set (the comma forces quoting) plus "never trimmed" and "doubling is the only change made to field content, quoted or not" | DETERMINED |
| `test_non_trigger_characters_are_not_quoted` | "nothing else about a field causes it to be quoted" and "tabs, semicolons, `#`, backslashes and non-ASCII are likewise not triggers" | DETERMINED |
| `test_empty_field_is_written_as_nothing` | "An empty field is zero characters, not `\"\"` — `non-escaped` is `*TEXTDATA`, which permits none, and an empty field holds no trigger — so a record of three empty fields is `,,` plus its CRLF." | DETERMINED |
| `test_record_with_zero_fields_is_a_bare_crlf` | "A record with no fields at all writes just its CRLF, an empty line, indistinguishable on the wire from one empty field; that is our call, not the RFC's … and such a record is written rather than rejected." | DETERMINED |
| `test_ragged_records_are_written_as_given` | "Clause 4's equal field count per line is advisory and we do not enforce it: ragged records go out exactly as given, each with its own count" | DETERMINED |
| `test_empty_table_returns_the_empty_string` | "Empty `rows` returns `\"\"`." | DETERMINED |
| `test_worked_example_from_the_ticket` | composition of the rules above; the trailing-empty-field and zero-field parts are shown outright by "So `write_csv([[\"2\", \"Portland, OR\", \"\"], []])` returns `'2,\"Portland, OR\",\r\n\r\n'`." | DETERMINED |
| `test_input_is_not_mutated` | "Pure — do not mutate `rows` or any record in it." | DETERMINED |
| `test_non_str_field_raises_type_error_naming_the_type` (7 params: `1`, `0`, `None`, `True`, `3.5`, `b"bytes"`, `["x"]`) | "Every field value must be a `str`; anything else — `int`, `bool`, `None`, `bytes` — raises `TypeError` rather than being stringified. The message must name the offending Python type (for an integer field, the text `int` appears in it)." — "anything else" covers `float` and `list`, which the test also passes | DETERMINED |

## Changes made during the audit

One sentence was strengthened after a first pass. The draft stated verbatim
preservation only for a lone CR/LF, which left `test_field_containing_crlf_is_quoted_and_preserved`
and `test_padding_survives_when_the_field_is_quoted_for_another_reason`
resting on inference rather than on text. The clause "and doubling is the only
change made to field content, quoted or not" was added to the escaping
paragraph, making verbatim content general and explicit.

## Open questions deliberately left open

Both open questions from `task.yaml` remain unresolved by the terse ticket:

- The signature types `rows` as `list[list[str]]`; the ticket never says
  whether a tuple or other non-list sequence is accepted or rejected, and no
  sentence was added about it.
- The ticket requires only that the `TypeError` message name the offending
  Python type. It does not say whether the message must also locate the row
  and field position, so that remains open.
