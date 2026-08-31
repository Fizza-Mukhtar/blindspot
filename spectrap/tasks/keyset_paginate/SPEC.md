# FEED-2291 — Keyset pagination for the activity feed

**Component:** `feed/pagination`
**Reporter:** Marco (Growth)
**Consumers:** the mobile activity feed, the web "load more" button, the digest mailer

## Background

The activity feed still pages with `OFFSET`. On a busy account the offset drifts
every time a new event lands, so subscribers see the same item twice or miss one
entirely, and page 40 costs forty times what page 1 costs. We are moving the feed
onto keyset (seek-method) pagination as described in
<https://use-the-index-luke.com/no-offset>: instead of counting rows to skip, each
page carries forward the sort key of its own last row, and the next page asks for
the rows that sort strictly after it.

The part that bit us in the prototype is that our sort key is **not unique on its
own**. `created_at` is a whole-second Unix timestamp and a burst of activity
routinely produces six or seven events in the same second. A cursor that carries
only the timestamp cannot say *where inside that second* the previous page
stopped, so the page boundary either eats the rest of the second or replays it
forever. The fix, and the thing this ticket is about, is that the cursor must
carry the whole sort key.

## What to build

```python
def page(rows: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    ...
```

`rows` is the candidate set of feed entries. Every row is a dict with at least an
`"id"` (a positive `int`) and a `"created_at"` (a non-negative `int`, whole
seconds). Rows may carry any number of other keys; those are payload and must
come back untouched. Ids are unique across the feed. **The rows arrive in no
particular order** — they come off a union of several sources — so the function
does its own ordering; do not assume the caller sorted them.

Return `(page_rows, next_cursor)`.

## Feed order

The feed reads newest first: order by `created_at` **descending**, and where two
rows share a `created_at`, by `id` **descending** as the tie-break. Because ids
are unique this is a strict total order — for any two distinct rows exactly one
precedes the other.

## The cursor

A cursor is the string `"<created_at>:<id>"` built from the **last row of the
page that was just returned** — both components, decimal, no spaces, no padding
beyond what the numbers need. Both halves matter: the cursor names a *position in
the total order*, not a timestamp.

When `cursor` is `None` the caller wants the first page: every row is a
candidate.

When `cursor` is given, parse it into `(c_created_at, c_id)` and keep exactly
those rows that come **strictly after that position in the feed order**, i.e.

```
row["created_at"] < c_created_at
   or (row["created_at"] == c_created_at and row["id"] < c_id)
```

Equivalently, `(created_at, id) < (c_created_at, c_id)` compared as a tuple,
because descending order over the pair reverses to ascending "have we passed it
yet". Filtering on `created_at` alone with `<` silently drops the rest of a
second; filtering with `<=` replays it. Neither is acceptable — the union of all
pages must be the whole feed, each row exactly once.

The cursor is a position, not a lookup. There is no requirement that a row with
that `(created_at, id)` still exists — the referenced event may have been deleted
or edited between requests, and paging must carry on from where it pointed
regardless.

## Page size and the end of the feed

Take the first `limit` candidates in feed order; that list is `page_rows`.

`next_cursor` is `None` exactly when the page just returned exhausts the
candidates — that is, when `limit` candidates or fewer remained. Otherwise it is
the cursor string for the last row of `page_rows`. In particular, when a page
lands exactly on the final row of the feed the answer is `None`; do not hand back
a cursor that would only ever produce an empty page.

An empty candidate set returns `([], None)` — that includes an empty `rows`, and
a cursor that has already run off the end of the feed.

## Worked example

```python
rows = [
    {"id": 4, "created_at": 300},
    {"id": 9, "created_at": 200},
    {"id": 7, "created_at": 200},
    {"id": 2, "created_at": 200},
    {"id": 5, "created_at": 100},
]

page(rows, None,     2)  ->  ([id 4, id 9], "200:9")
page(rows, "200:9",  2)  ->  ([id 7, id 2], "200:2")
page(rows, "200:2",  2)  ->  ([id 5],        None)
```

Note the second call: the cursor sits in the middle of the three rows stamped
`200`, and ids `7` and `2` are still owed to the caller.

## Errors

- `limit` must be an `int` of at least 1. Anything else — `0`, a negative number,
  a non-integer — raises `ValueError`.
- A malformed cursor raises `ValueError`. Well-formed means: a `str` consisting of
  a non-empty run of ASCII digits, a single `:`, and another non-empty run of
  ASCII digits. `"12"`, `"12:"`, `":3"`, `"12:3:4"`, `"12 : 3"`, `"-1:3"`,
  `"1.0:3"`, `""` and any non-string that is not `None` are all malformed.

Raise before doing any work; a bad argument never yields a partial page.

## Out of scope

- Validating the contents of `rows`. Upstream guarantees the `id`/`created_at`
  shape described above.
- Any opaque or signed cursor encoding (base64, HMAC). We will layer that on top
  later; for now the wire format is the bare `"<created_at>:<id>"` string.
- Ascending ("oldest first") feeds, and paging backwards to the previous page.
- Deduplication across sources, and any caching. The function is pure and must
  not mutate `rows`.
