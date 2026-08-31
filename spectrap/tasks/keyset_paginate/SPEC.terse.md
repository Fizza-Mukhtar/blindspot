# FEED-2291 — Keyset pagination for the activity feed

**Component:** `feed/pagination`
**Reporter:** Marco (Growth)

## Background

`OFFSET` paging drifts every time a new event lands, so subscribers see an item
twice or miss one. Moving to the seek method
(<https://use-the-index-luke.com/no-offset>): each page carries forward the sort
key of its own last row, and the next page asks for the rows sorting strictly
after it. `created_at` is a whole-second Unix timestamp and a burst routinely
stamps several events with the same second, so it is not unique on its own.

## What to build

```python
def page(rows: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    ...
```

Each row has at least an `"id"` (positive `int`, unique across the feed) and a
`"created_at"` (non-negative `int`, whole seconds); other keys are payload and
must come back untouched. `rows` arrives off a union of sources unordered, so
`page` orders it itself — newest first: `created_at` descending, `id` descending
as the tie-break, a strict total order since ids are unique. Return
`(page_rows, next_cursor)`.

## Cursor and paging

A cursor is `"<created_at>:<id>"`, both decimal, no spaces, no padding beyond
what the numbers need, built from the last row of the page just returned. It names a position in that order, not a
timestamp, so a supplied cursor parses to `(c_created_at, c_id)` and we keep
exactly the rows strictly after that position: those with
`created_at < c_created_at`, or with `created_at == c_created_at` and
`id < c_id`; going on the timestamp alone either eats the rest of that second or
replays it, and the union of all pages must be the whole feed with each row
exactly once. A `cursor` of `None` is the first page: every row is a candidate.
The cursor is a position, not a lookup: the row it names may since have been
deleted, and paging carries on from that position anyway.

`page_rows` is the first `limit` candidates in feed order. `next_cursor` is the
cursor for the last row of `page_rows`, except `None` whenever that page
exhausted the candidates (`limit` or fewer remained), so a page landing on the
final row reports `None`, not a cursor whose only possible page is empty. An
empty candidate set gives `([], None)` — an empty `rows`, or a cursor already
run off the end.

Over `(created_at, id)` pairs `(300,4) (200,9) (200,7) (200,2) (100,5)`, limit 2
pages as `[4, 9]`/`"200:9"`, then `[7, 2]`/`"200:2"`, then `[5]`/`None`.

## Errors

Raise `ValueError`, before doing any work, if `limit` is not an `int` of at
least 1, or if the cursor is malformed. Well-formed is a `str` of a non-empty
run of ASCII digits, a single `:`, and another non-empty run of ASCII digits;
`"12"`, `":3"`, `"-1:3"` and any non-string other than `None` are not.

## Out of scope

- Validating row contents; upstream guarantees the shape above.
- Opaque or signed cursor encodings (base64, HMAC); the wire format stays bare.
- Ascending feeds, and backwards paging.
- Dedup and caching. The function is pure and must not mutate `rows`.
