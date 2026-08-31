# CDN-2291 — Resolve a client `Range:` header into concrete byte offsets

**Component:** `edge/rangeresolve`
**Reporter:** Marcus (Edge Delivery)
**Consumers:** the origin-shield byte server, the video seek path, the resumable-download endpoint

## Background

Our edge nodes currently hand the raw `Range:` header string down to three
different call sites, and all three parse it slightly differently. The video
seek path is off by one byte at the tail of every segment, and the resumable
download endpoint answers `416 Range Not Satisfiable` whenever a client asks
for more bytes than the object actually has — which well-behaved clients do all
the time, because that is exactly how you ask for "the rest of it".

We want one function that turns a header into concrete offsets, so the byte
server stops guessing. The governing text is RFC 7233 section 2.1
(<https://www.rfc-editor.org/rfc/rfc7233.html#section-2.1>).

## What to build

```python
def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    ...
```

`header` is the *value* of the `Range` header field, e.g. `"bytes=0-499"` —
the field name and colon have already been stripped by the request parser.
`length` is the exact current length in bytes of the representation we are
about to serve; the storage layer always knows it, so it is passed in rather
than looked up.

Return one `(first, last)` pair per range the header asks for. **Both offsets
are inclusive**, the way the RFC defines them: `(0, 499)` is five hundred
bytes, and `(0, 0)` is a single byte. The pairs come back **in the order the
header lists them**. Do not merge overlapping or adjacent ranges, do not sort
them, do not drop duplicates — the byte server needs to emit one multipart
part per requested range, in the requested order, and it is the caller's job to
decide whether a pathological request is worth serving.

## Header syntax we accept

```
bytes=<byte-range-spec> [ , <byte-range-spec> ]...
```

where each spec is one of:

| form | meaning |
| --- | --- |
| `first-last` | from `first` to `last`, inclusive |
| `first-` | from `first` to the end of the representation |
| `-suffix` | the final `suffix` bytes of the representation |

`first`, `last` and `suffix` are one or more ASCII digits. Leading zeroes are
permitted by the grammar and carry no meaning, so `bytes=007-009` means the
same as `bytes=7-9`.

The unit token is compared case-insensitively, so `Bytes=0-0` is accepted.
Leading and trailing spaces and horizontal tabs around the whole header value
are ignored, and so are spaces and tabs around each comma-separated element.
Following the list rule in RFC 7230 section 7, **empty list elements are
legal and are skipped**: `bytes=0-0, ,-1` asks for two ranges. There must be
at least one non-empty element. No whitespace is allowed around the `=` or
inside a spec, so `bytes = 0-1` and `bytes=0 - 1` are not valid.

## Resolving each spec

Let `length` be the representation length.

1. `first-last`: if `last` is greater than or equal to `length`, it is
   **clamped to `length - 1`**. This is not an error and it is emphatically not
   a 416 — the RFC says a last-byte-pos at or past the end "is taken to be
   equal to one less than the current length". So `bytes=0-9999` against a
   1000-byte object resolves to `(0, 999)`, the whole thing.
2. `first-`: runs to the last byte, i.e. `(first, length - 1)`.
3. `-suffix`: the final `suffix` bytes, i.e. `(length - suffix, length - 1)`.
   If `suffix` is greater than or equal to `length` the whole representation is
   returned: `bytes=-5000` against a 1000-byte object resolves to `(0, 999)`.
   This too is not an error.

A spec is **unsatisfiable** when, and only when, one of these holds:

- it is a `first-last` or `first-` spec whose `first` is greater than or equal
  to `length` (there is no such byte to start at); or
- it is a `-suffix` spec whose `suffix` is zero. `bytes=-0` asks for the last
  zero bytes, which no representation can provide.

Note the asymmetry that follows from rule 1: an out-of-reach `last` is
harmless, an out-of-reach `first` is not.

## Combining the results

Unsatisfiable specs are **dropped silently** as long as at least one spec in
the header is satisfiable; the remaining pairs keep their original relative
order. Against a 1000-byte object, `bytes=100-199,5000-5100,0-0` returns
`[(100, 199), (0, 0)]`.

If **every** spec in the header is unsatisfiable, raise `UnsatisfiableRange` —
define this exception in your module. It must derive from `Exception` directly
and **must not** be a subclass of `ValueError`; the request pipeline catches
`ValueError` to mean "we could not parse the request" and turns it into a 400,
whereas an `UnsatisfiableRange` becomes a 416, and the two must not be
confused.

## Malformed headers are ignored, not rejected

If the header does not match the syntax above — a unit we do not understand
(`items=0-5`), garbage where digits belong (`bytes=abc`), a missing `=`, an
empty range set (`bytes=`), a bare `-`, whitespace in the wrong place, or a
`first-last` spec whose `last` is less than its `first` (RFC 7233 section 2.1:
"A byte-range-spec is invalid if the last-byte-pos value is present and less
than the first-byte-pos") — then per RFC 7233 section 3.1 the header is
**ignored entirely** and we serve the whole representation. Concretely,
`resolve_range` returns `[(0, length - 1)]`. It does not raise, and it does not
fall back to whatever prefix of the list happened to parse: one bad element
poisons the whole header, so `bytes=0-1,5-3` also returns the whole object.

## Worked example

A 1000-byte object, header `bytes=0-0,-1`, which is the RFC's own idiom for
"the first and last byte":

```
"bytes=0-0,-1", 1000  ->  [(0, 0), (999, 999)]
```

and a few more against the same 1000-byte object:

```
"bytes=0-499"          -> [(0, 499)]      # first 500 bytes
"bytes=500-999"        -> [(500, 999)]    # second 500 bytes
"bytes=500-"           -> [(500, 999)]    # same thing, open ended
"bytes=-500"           -> [(500, 999)]    # same thing, as a suffix
"bytes=-5000"          -> [(0, 999)]      # suffix longer than the object
"bytes=0-9999"         -> [(0, 999)]      # last-byte-pos clamped
"bytes=-0"             -> UnsatisfiableRange
"bytes=1000-"          -> UnsatisfiableRange
"bytes=2-1"            -> [(0, 999)]      # malformed, so ignored
```

## Arguments and errors

Validate the arguments first: `header` must be a `str` and `length` must be an
`int` that is zero or greater. Anything else is a programming error on our
side, so raise `ValueError`.

Then handle the empty representation: **if `length` is 0 the object has no
bytes at all**, so nothing can be served for it, and `resolve_range` raises
`UnsatisfiableRange` whatever the header says — including for a header that
would otherwise be ignored as malformed, since there is no whole object to fall
back to.

## Out of scope

- Producing the `Content-Range` response header or the multipart body.
- Capping, coalescing or rejecting abusive range sets. Hand back what was
  asked for; the byte server decides what it is willing to serve.
- Range units other than `bytes`, and conditional `If-Range` handling.
- Any I/O. The function is pure and depends on nothing but its two arguments.
