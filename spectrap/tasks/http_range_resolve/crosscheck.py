"""Independent oracle for CDN-2291 / http_range_resolve.

Built from RFC 7233 section 2.1 + section 3.1 and SPEC.md, deliberately with a
different shape from the obvious regex-and-loop implementation:

  * the header value is taken apart by a hand-written index scanner that walks
    the ABNF productions of RFC 7233 section 2.1 character by character
    (bytes-unit "=" byte-range-set, byte-range-spec = first-byte-pos "-"
    [ last-byte-pos ], suffix-byte-range-spec = "-" suffix-length), with no
    regular expressions and no int()-based digit sniffing -- int() would happily
    swallow "+5", "1_0" and full-width unicode digits, none of which are 1*DIGIT;
  * satisfiability and clamping are then applied by a literal decision table
    (_DECISIONS) keyed on the classification of the parsed spec, rather than by
    nested if/else, so that the asymmetry RFC 7233 section 2.1 describes between
    the two ends of a range is visible as data instead of control flow.
"""

from __future__ import annotations

ORACLE_NOTES = """\
Oracle basis
------------
Hand-written ABNF scanner over RFC 7233 section 2.1's grammar plus a decision
table for the resolve/clamp/drop step.  No regex, no int()-parsing of digits
(int() accepts '+5', '1_0' and non-ASCII digits, which are not 1*DIGIT).

Clauses checked against https://www.rfc-editor.org/rfc/rfc7233.html
  * 2.1 ABNF: byte-ranges-specifier = bytes-unit "=" byte-range-set ;
    byte-range-set = 1#( byte-range-spec / suffix-byte-range-spec ) ;
    byte-range-spec = first-byte-pos "-" [ last-byte-pos ] ;
    suffix-byte-range-spec = "-" suffix-length ; all three positions are
    1*DIGIT, so leading zeroes are legal and "-" alone is not a spec.
  * 2.1 "Byte offsets start at zero" and both ends inclusive: bytes=0-499 is
    the first 500 bytes.
  * 2.1 "A byte-range-spec is invalid if the last-byte-pos value is present
    and less than the first-byte-pos."  -> bytes=2-1 is a *syntax/validity*
    failure, not an unsatisfiable range.
  * 2.1 "If the last-byte-pos value is absent, or if the value is greater than
    or equal to the current length of the representation data, the byte range
    is interpreted as the remainder of the representation" -> clamp to
    length-1, never a 416.
  * 2.1 satisfiability: "a byte-range-set is satisfiable if it contains at
    least one byte-range-spec with a first-byte-pos that is less than the
    current length of the representation, or at least one
    suffix-byte-range-spec with a non-zero suffix-length."  This is the exact
    source of the asymmetry: an overrunning last-byte-pos is clamped, an
    overrunning first-byte-pos is not satisfiable, and suffix-length 0 is not
    satisfiable while an oversized suffix-length is (it simply names the whole
    representation).
  * 2.1 worked examples for a 10000-byte representation (bytes=0-499,
    bytes=500-999, bytes=-500, bytes=9500-, bytes=0-0,-1,
    bytes=500-600,601-999, bytes=500-700,601-999) -- these are copied straight
    into KNOWN_VALUES below.
  * 3.1 "An origin server MUST ignore a Range header field that contains a
    range unit it does not understand", and "A server MAY ignore the Range
    header field."
  * RFC 7230 section 7 list rule, for empty list elements and OWS.

Ambiguities / things I think SPEC.md gets wrong
-----------------------------------------------
1. SPEC.md attributes "ignore the whole header when it is malformed" to
   "RFC 7233 section 3.1".  Section 3.1 does not say that.  What section 3.1
   actually says is the opposite for invalid ranges: "If all of the
   preconditions are true, the server supports the Range header field for the
   target resource, and the specified range(s) are invalid or unsatisfiable,
   the server SHOULD send a 416 (Range Not Satisfiable) response."  The only
   MUST-ignore in 3.1 is for an unrecognised *range unit*; everything else
   rests on the permissive "A server MAY ignore the Range header field."  So
   the ticket's behaviour (ignore -> whole representation) is *permitted* by
   the RFC but the citation is wrong, and for "bytes=2-1" the RFC's own SHOULD
   points at 416, not at serving the whole object.  This oracle follows the
   ticket, because the ticket is the contract; flagging the miscitation.
2. Whitespace after the "=".  SPEC.md says both "No whitespace is allowed
   around the `=` ... so `bytes = 0-1` ... [is] not valid" and "spaces and tabs
   around each comma-separated element are ignored".  The first element of the
   byte-range-set sits immediately after the "=", so the two sentences collide
   on "bytes= 0-1" and on "bytes= ,0-1" (which the fuzz generator produces,
   because its separator pool contains " ,"  and it inserts empty elements at
   index 0).  RFC 7230 section 7's expansion `1#element => *( "," OWS )
   element *( OWS "," [ OWS element ] )` is strict here: OWS may not precede
   the first element unless a comma comes first, so "bytes= 0-1" and
   "bytes= ,0-1" are both strictly invalid.  I implemented the *permissive*
   reading (strip OWS around every element, including the first), because
   SPEC.md's element rule is stated unconditionally and its only cited
   counter-example, "bytes = 0-1", already fails on the unit token.  This is
   genuine under-determination in the ticket.
3. `length` type check: bool is a subclass of int in Python, so
   resolve_range("bytes=0-0", True) is accepted here as length 1.  SPEC.md does
   not say.  Not reachable from the generator.
4. Ordering of the two error rules: SPEC.md says validate the arguments
   *first*, then the length == 0 rule, so resolve_range("bytes=0-0", -1) is a
   ValueError rather than an UnsatisfiableRange.  Implemented that way.
5. SPEC.md's "empty list elements are legal and are skipped" plus "There must
   be at least one non-empty element" means "bytes=" and "bytes=,," are
   malformed and therefore resolve to the whole representation -- not to
   UnsatisfiableRange.  Worth stating explicitly; it is easy to read the two
   sentences as producing a 416.

Reference defects found (see the last two KNOWN_VALUES blocks)
--------------------------------------------------------------
A. The reference trims LF from the header value.  resolve_range("bytes=0-1\\n",
   1000) returns [(0, 1)] there and [(0, 999)] here.  RFC 7230 s3.2.3 defines
   OWS = *( SP / HTAB ); LF is not OWS, and RFC 7230 s3.2 excludes bare CR/LF
   from field-value entirely.  SPEC.md agrees ("spaces and horizontal tabs").
   It is specifically LF and not str.strip(): "bytes=0-1\\r", "\\x0b", "\\x0c",
   NBSP and EM SPACE all correctly come back as malformed on both sides, so the
   reference's OWS set is a hand-written one that wrongly contains "\\n".
B. The reference validates digits with a Unicode-aware predicate
   (str.isdecimal() or a bare int()), so non-ASCII decimal digits parse.
   resolve_range("bytes=\\uff10-\\uff19", 1000) -> [(0, 9)] there, [(0, 999)]
   here; resolve_range("bytes=\\u0660-\\u0669", 1000) -> [(0, 9)] there;
   resolve_range("bytes=-\\u0665", 1000) -> [(995, 999)] there.  RFC 5234's
   core rule is DIGIT = %x30-39 and SPEC.md says "one or more ASCII digits".
   The predicate is isdecimal()/int() and not isdigit(), because SUPERSCRIPT
   TWO and CIRCLED DIGIT ONE (isdigit() True, isdecimal() False) are rejected
   by both sides.
Neither defect is reachable from generators.py, which emits ASCII-only headers.
"""


class UnsatisfiableRange(Exception):
    """Every requested range fell outside the representation (-> HTTP 416)."""


# --- ABNF primitives -------------------------------------------------------

_DIGIT = frozenset("0123456789")   # 1*DIGIT is ASCII-only, deliberately
_OWS = frozenset(" \t")            # RFC 7230: OWS = *( SP / HTAB )

# Classification tags produced by the scanner.
_EMPTY = "empty"        # an empty list element -- skipped per RFC 7230 s7
_CLOSED = "closed"      # byte-range-spec with last-byte-pos present
_OPEN = "open"          # byte-range-spec with last-byte-pos absent
_SUFFIX = "suffix"      # suffix-byte-range-spec
_BAD = "bad"            # does not match the grammar at all


def _trim_ows(text: str) -> str:
    """Trim SP/HTAB only -- str.strip() would also eat CR, LF, FF, VT."""
    start, stop = 0, len(text)
    while start < stop and text[start] in _OWS:
        start += 1
    while stop > start and text[stop - 1] in _OWS:
        stop -= 1
    return text[start:stop]


def _read_digits(text: str, index: int) -> tuple[int, int | None]:
    """Read 1*DIGIT at ``index``.  Returns (next_index, value|None)."""
    start = index
    while index < len(text) and text[index] in _DIGIT:
        index += 1
    if index == start:
        return start, None
    # Leading zeroes are permitted by the grammar and carry no meaning.
    value = 0
    for character in text[start:index]:
        value = value * 10 + (ord(character) - 48)
    return index, value


def _classify(element: str) -> tuple:
    """Walk one list element against the section 2.1 ABNF, by hand."""
    element = _trim_ows(element)
    if element == "":
        return (_EMPTY,)

    cursor = 0
    end = len(element)

    if element[cursor] == "-":
        # suffix-byte-range-spec = "-" suffix-length
        cursor += 1
        cursor, suffix = _read_digits(element, cursor)
        if suffix is None or cursor != end:
            return (_BAD,)
        return (_SUFFIX, suffix)

    # byte-range-spec = first-byte-pos "-" [ last-byte-pos ]
    cursor, first = _read_digits(element, cursor)
    if first is None:
        return (_BAD,)
    if cursor >= end or element[cursor] != "-":
        return (_BAD,)
    cursor += 1
    if cursor == end:
        return (_OPEN, first)
    cursor, last = _read_digits(element, cursor)
    if last is None or cursor != end:
        return (_BAD,)
    return (_CLOSED, first, last)


def _split_list(text: str) -> list[str]:
    """Split a #rule list on commas, by hand (no str.split, no regex)."""
    elements: list[str] = []
    piece: list[str] = []
    for character in text:
        if character == ",":
            elements.append("".join(piece))
            piece = []
        else:
            piece.append(character)
    elements.append("".join(piece))
    return elements


# --- the decision table ----------------------------------------------------
#
# Keyed by (tag, overruns?) where "overruns?" is the single boolean that
# RFC 7233 s2.1 makes decisive for that shape of spec.  The value is either the
# sentinel DROP (the spec is unsatisfiable and gets dropped) or a resolver.

DROP = object()

_DECISIONS = {
    # byte-range-spec with last-byte-pos: unsatisfiable iff first >= length.
    # Otherwise last is clamped: ">= current length -> remainder of the
    # representation" (s2.1).
    (_CLOSED, True): DROP,
    (_CLOSED, False): lambda first, last, length: (first, min(last, length - 1)),
    # byte-range-spec without last-byte-pos: "interpreted as the remainder".
    (_OPEN, True): DROP,
    (_OPEN, False): lambda first, _last, length: (first, length - 1),
    # suffix-byte-range-spec: unsatisfiable iff suffix-length is zero; an
    # oversized suffix simply names the whole representation.
    (_SUFFIX, True): DROP,
    (_SUFFIX, False): lambda suffix, _unused, length: (max(0, length - suffix), length - 1),
}


def _overruns(parsed: tuple, length: int) -> bool:
    """The one boolean the decision table keys on, per shape."""
    tag = parsed[0]
    if tag is _SUFFIX or tag == _SUFFIX:
        return parsed[1] == 0            # "-0" can never be satisfied
    return parsed[1] >= length           # first-byte-pos beyond the last byte


def oracle(header, length):
    # 1. Argument validation ("a programming error on our side").
    if not isinstance(header, str):
        raise ValueError("header must be a str")
    if not isinstance(length, int):
        raise ValueError("length must be an int")
    if length < 0:
        raise ValueError("length must be >= 0")

    # 2. Empty representation: nothing can ever be served, not even the
    #    "ignore the header and serve the whole thing" fallback.
    if length == 0:
        raise UnsatisfiableRange("representation is empty")

    whole = [(0, length - 1)]

    # 3. byte-ranges-specifier = bytes-unit "=" byte-range-set
    value = _trim_ows(header)
    equals = value.find("=")
    if equals < 0:
        return whole
    unit = value[:equals]
    if unit.lower() != "bytes":       # includes the "bytes " / " bytes" cases
        return whole

    elements = _split_list(value[equals + 1:])

    # 4. Classify every element first; one bad element poisons the header.
    parsed = [_classify(element) for element in elements]
    if any(item[0] == _BAD for item in parsed):
        return whole
    if all(item[0] == _EMPTY for item in parsed):
        return whole                  # "at least one non-empty element"

    resolved: list[tuple[int, int]] = []
    for item in parsed:
        tag = item[0]
        if tag == _EMPTY:
            continue
        if tag == _CLOSED and item[2] < item[1]:
            # s2.1: "invalid if the last-byte-pos value is present and less
            # than the first-byte-pos" -- a validity failure, so the whole
            # header is ignored rather than this spec being dropped.
            return whole
        action = _DECISIONS[(tag, _overruns(item, length))]
        if action is DROP:
            continue
        second = item[2] if tag == _CLOSED else None
        resolved.append(action(item[1], second, length))

    if not resolved:
        raise UnsatisfiableRange(header)
    return resolved


# --- values taken from the standard's own text -----------------------------
#
# RFC 7233 s2.1 works its examples against "a representation of length 10000",
# so most of these use length 10000 and are copied from the RFC verbatim.

KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # s2.1: "The first 500 bytes (byte offsets 0-499, inclusive)".
    (("bytes=0-499", 10000), {}, [(0, 499)]),
    # s2.1: "The second 500 bytes (byte offsets 500-999, inclusive)".
    (("bytes=500-999", 10000), {}, [(500, 999)]),
    # s2.1: "The final 500 bytes (byte offsets 9500-9999, inclusive)".
    (("bytes=-500", 10000), {}, [(9500, 9999)]),
    # s2.1: "Or: bytes=9500-" -- same range, open-ended form.
    (("bytes=9500-", 10000), {}, [(9500, 9999)]),
    # s2.1: "The first and last bytes only (bytes 0 and 9999)".
    (("bytes=0-0,-1", 10000), {}, [(0, 0), (9999, 9999)]),
    # s2.1: "Other valid (but not canonical) specifications of the second 500
    # bytes" -- note neither is merged or reordered.
    (("bytes=500-600,601-999", 10000), {}, [(500, 600), (601, 999)]),
    (("bytes=500-700,601-999", 10000), {}, [(500, 700), (601, 999)]),
    # s2.1: last-byte-pos absent -> "the remainder of the representation".
    (("bytes=0-", 10000), {}, [(0, 9999)]),
    # s2.1: last-byte-pos ">= the current length" -> remainder, NOT a 416.
    (("bytes=0-9999", 1000), {}, [(0, 999)]),
    (("bytes=999-100000", 1000), {}, [(999, 999)]),
    # s2.1 satisfiability: oversized suffix-length is still non-zero, so the
    # set is satisfiable and names the whole representation.
    (("bytes=-5000", 1000), {}, [(0, 999)]),
    # s2.1 satisfiability: no spec with first-byte-pos < length, and no
    # suffix-spec with non-zero suffix-length -> unsatisfiable.
    (("bytes=-0", 1000), {}, ("raises", "UnsatisfiableRange")),
    (("bytes=1000-", 1000), {}, ("raises", "UnsatisfiableRange")),
    (("bytes=1000-1200", 1000), {}, ("raises", "UnsatisfiableRange")),
    # ... but one satisfiable spec makes the whole set satisfiable; the
    # unsatisfiable ones are dropped and the order is preserved.
    (("bytes=100-199,5000-5100,0-0", 1000), {}, [(100, 199), (0, 0)]),
    # s2.1: "invalid if the last-byte-pos value is present and less than the
    # first-byte-pos" -> header ignored, whole representation.
    (("bytes=2-1", 1000), {}, [(0, 999)]),
    (("bytes=0-1,5-3", 1000), {}, [(0, 999)]),
    # s3.1: "MUST ignore a Range header field that contains a range unit it
    # does not understand".
    (("items=0-5", 1000), {}, [(0, 999)]),
    # Grammar failures: "-" alone is not a suffix-byte-range-spec (1*DIGIT),
    # "abc" is not 1*DIGIT, and an empty byte-range-set is not 1#(...).
    (("bytes=-", 1000), {}, [(0, 999)]),
    (("bytes=abc", 1000), {}, [(0, 999)]),
    (("bytes=", 1000), {}, [(0, 999)]),
    (("bytes=0-1", 0), {}, ("raises", "UnsatisfiableRange")),
    (("bytes=garbage", 0), {}, ("raises", "UnsatisfiableRange")),
    (("bytes=0-0", -1), {}, ("raises", "ValueError")),
    ((None, 10), {}, ("raises", "ValueError")),
    # bytes-unit is case-insensitive; leading zeroes carry no meaning.
    (("Bytes=007-009", 1000), {}, [(7, 9)]),
    # RFC 7230 s7 list rule: empty elements are parsed and ignored.
    (("bytes=0-0, ,-1", 1000), {}, [(0, 0), (999, 999)]),

    # ---- probes into the corners the fuzz generator never reaches ----
    # OWS handling.  SPEC.md's "spaces and tabs around each comma-separated
    # element are ignored" vs RFC 7230 s7's stricter
    # `*( "," OWS ) element *( OWS "," [ OWS element ] )`.
    (("  bytes=0-1\t", 1000), {}, [(0, 1)]),      # OWS around the whole value
    (("bytes= 0-1", 1000), {}, [(0, 1)]),         # OWS after "=" (ambiguous)
    (("bytes= ,0-1", 1000), {}, [(0, 1)]),        # OWS then empty element
    (("bytes=0-1,", 1000), {}, [(0, 1)]),         # trailing empty element
    (("bytes=,0-1", 1000), {}, [(0, 1)]),         # leading empty element
    (("bytes=,,", 1000), {}, [(0, 999)]),         # no non-empty element
    (("bytes=0-1\n", 1000), {}, [(0, 999)]),      # LF is not OWS -> malformed
    (("bytes\t=0-1", 1000), {}, [(0, 999)]),      # OWS before "=" kills the unit
    # bytes-unit is a case-insensitive token.
    (("BYTES=0-0", 1000), {}, [(0, 0)]),
    # 1*DIGIT is ASCII-only and has no sign / separator.
    (("bytes=+5-9", 1000), {}, [(0, 999)]),
    (("bytes=1_0-20", 1000), {}, [(0, 999)]),
    (("bytes=０-９", 1000), {}, [(0, 999)]),   # full-width digits
    # s2.1: "a server ought to ... be careful about overflows" -- arbitrarily
    # long decimals are legal 1*DIGIT.
    (("bytes=0-0000000000000000000000005", 1000), {}, [(0, 5)]),
    (("bytes=99999999999999999999999999-", 1000), {}, ("raises", "UnsatisfiableRange")),
    (("bytes=-99999999999999999999", 1000), {}, [(0, 999)]),
    # Extra "=" and trailing parameters are not part of byte-range-set.
    (("bytes==0-1", 1000), {}, [(0, 999)]),
    (("bytes=0-1;q=1", 1000), {}, [(0, 999)]),
    (("bytes 0-1", 1000), {}, [(0, 999)]),
    # Mixed satisfiable / unsatisfiable suffix specs.
    (("bytes=-0,-0", 1000), {}, ("raises", "UnsatisfiableRange")),
    (("bytes=-0,0-0", 1000), {}, [(0, 0)]),
    (("bytes=0-0,0-0", 1000), {}, [(0, 0), (0, 0)]),   # duplicates preserved
    (("bytes=999-,-1", 1000), {}, [(999, 999), (999, 999)]),
    # Single-byte representation: every boundary rule at once.
    (("bytes=0-0", 1), {}, [(0, 0)]),
    (("bytes=1-", 1), {}, ("raises", "UnsatisfiableRange")),
    (("bytes=-1", 1), {}, [(0, 0)]),
    (("bytes=-2", 1), {}, [(0, 0)]),
    (("bytes=0-5", 1), {}, [(0, 0)]),
    # Argument validation.
    ((b"bytes=0-0", 1000), {}, ("raises", "ValueError")),
    (("bytes=0-0", 1.0), {}, ("raises", "ValueError")),
    (("bytes=0-0", "1000"), {}, ("raises", "ValueError")),

    # ---- probes isolating the two reference defects ----
    # RFC 7230 s3.2.3: OWS = *( SP / HTAB ).  Nothing else may be trimmed, and
    # RFC 7230 s3.2 forbids bare CR/LF/CTLs in a field-value at all.
    (("bytes=0-1\r", 1000), {}, [(0, 999)]),
    (("bytes=0-1\x0b", 1000), {}, [(0, 999)]),
    (("bytes=0-1\x0c", 1000), {}, [(0, 999)]),
    (("\xa0bytes=0-1", 1000), {}, [(0, 999)]),        # NBSP is not OWS
    ((" bytes=0-1", 1000), {}, [(0, 999)]),      # EM SPACE is not OWS
    # RFC 5234 core rule: DIGIT = %x30-39.  SPEC.md: "one or more ASCII digits".
    (("bytes=٠-٩", 1000), {}, [(0, 999)]),            # Arabic-Indic digits
    (("bytes=-٥", 1000), {}, [(0, 999)]),
    (("bytes=0-²", 1000), {}, [(0, 999)]),       # SUPERSCRIPT TWO
    (("bytes=①-9", 1000), {}, [(0, 999)]),       # CIRCLED DIGIT ONE
]
