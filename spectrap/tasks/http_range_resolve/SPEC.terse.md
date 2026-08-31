# CDN-2291 — Resolve a client `Range:` header into concrete byte offsets

**Component:** `edge/rangeresolve`
**Reporter:** Marcus (Edge Delivery)

## Background

Three call sites each parse the raw `Range:` header their own way; the video
seek path is a byte short at every segment tail and the resumable download
endpoint 416s whenever a client asks for more bytes than the object has. One
function, so the byte server stops guessing. RFC 7233 §2.1 governs, §3.1
covers headers we ignore:
<https://www.rfc-editor.org/rfc/rfc7233.html#section-2.1>.

## What to build

```python
def resolve_range(header: str, length: int) -> list[tuple[int, int]]:
    ...
```

`header` is the field value only (`"bytes=0-499"`), name and colon already
stripped; `length` is the representation's exact current byte length, passed
in because storage knows it. Return one `(first, last)` pair per range asked
for, both offsets inclusive as the RFC defines them — `(0, 499)` is five
hundred bytes, `(0, 0)` is one — in the order the header lists them, with
nothing merged, sorted or de-duplicated; the byte server emits one part per
requested range and decides what it will serve.

## Parsing

We take `bytes=` then a comma-separated list of specs, each `first-last`,
`first-` or `-suffix`, with `first`/`last`/`suffix` one or more ASCII digits;
leading zeroes are legal and meaningless, so `bytes=007-009` is `bytes=7-9`.
The unit compares case-insensitively (`Bytes=0-0` is fine). Spaces and
horizontal tabs are ignored around the whole value and around each element,
but not around the `=` and not inside a spec, so `bytes = 0-1` and
`bytes=0 - 1` are bad. Per the RFC 7230 §7 list rule empty elements are skipped, not
rejected — `bytes=0-0, ,-1` is a two-range header — though at least one
non-empty element must be present.

## Resolving

`first-` runs to the end, `(first, length - 1)`; `-suffix` takes the final
`suffix` bytes, `(length - suffix, length - 1)`, and a `suffix` at or beyond
`length` yields the whole representation, so `bytes=-5000` on a 1000-byte
object is `(0, 999)`. A `last` greater than or equal to `length` is clamped to
`length - 1` — the RFC takes it "to be equal to one less than the current
length" — so `bytes=0-9999` on that object is `(0, 999)` too, not a failure. A
spec is unsatisfiable in exactly two cases: its `first` is greater than or
equal to `length`, leaving no byte to start at, or it is `-0`, asking for the
last zero bytes, which nothing can provide.

Unsatisfiable specs are dropped silently while some spec is still satisfiable,
survivors keeping their relative order, so `bytes=100-199,5000-5100,0-0`
against 1000 bytes gives `[(100, 199), (0, 0)]`. If every spec is
unsatisfiable, raise `UnsatisfiableRange`, defined in your module deriving
directly from `Exception` and **not** from `ValueError`: the pipeline reads
`ValueError` as a 400 and this has to be a 416.

## Headers we cannot parse

Anything not fitting that grammar — an unrecognised unit (`items=0-5`),
non-digits where digits belong (`bytes=abc`, `bytes=+5-9`, `bytes=0-1;q=1`), a
missing `=`, an empty range set, a bare `-`, the empty string, or a spec whose
`last` is below its `first`, which §2.1 calls invalid — is ignored entirely
per RFC 7233 §3.1 and we serve the whole representation, returning `[(0,
length - 1)]`. It does not raise, and one bad element poisons the whole header
rather than the good prefix surviving: `bytes=0-1,5-3` is the whole object
too.

## Arguments

Validate arguments first: `header` must be a `str` and `length` an `int` of
zero or more, anything else raises `ValueError`. Then the empty representation
— at `length` 0 there are no bytes to serve and no whole object to fall back
on, so `resolve_range` raises `UnsatisfiableRange` whatever the header says,
malformed ones included.

## Out of scope

`Content-Range` and multipart bodies; capping or coalescing abusive range sets
(the byte server decides); units other than `bytes`; `If-Range`. Pure
function, no I/O.
