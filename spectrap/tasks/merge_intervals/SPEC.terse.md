# SCHED-207 — Coalesce a room's booking intervals into busy blocks

**Component:** `scheduling/calendar`
**Reporter:** Marcus (Scheduling Platform)
**Consumers:** free/busy, utilisation report, double-booking guard

## Background

Free/busy hands back raw reservation rows, so a room booked 09:00–10:00 then
10:00–10:30 reports two blocks with a phantom gap at 10:00 that sales then book.
Cancelled rows aren't deleted either, just collapsed to `(615, 615)`-style
zero-width rows that mobile draws as 1px slivers. We want one function that turns
the raw rows into the room's real busy blocks.

## What to build

```python
def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    ...
```

Return a new list of `(start, end)` tuples sorted ascending by start; do not
mutate the input list or any entry in it.

Bookings are half-open intervals `[start, end)` in whole minutes since midnight —
start minute booked, end minute not — the convention the rest of the stack uses
(EWD 831, <https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD831.html>).
So a boundary between output blocks must mean at least one genuinely free minute
lies between them: `[60, 120)` and `[120, 180)` leave none free and are the
single block `[60, 180)`, whereas `[60, 120)` and `[121, 180)` stay apart because
minute 120 is free. Every minute covered by at least one non-empty booking falls
in exactly one output block, no other minute does. A row whose start equals its
end covers no minutes — that's a collapsed cancellation — so drop those before
merging; they must not reach the output and, having no duration, must not glue
two blocks together, so `[(0, 60), (90, 90), (120, 180)]` is
`[(0, 60), (120, 180)]`. If every row is like that you get `[]`, as you do for
empty input. No output block is zero-length, and entries are plain `tuple`s of
two `int`s in that order. So:

```python
merge_bookings([(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)])
# -> [(480, 630), (690, 720)]
```

## Input

Straight off a database cursor: any order, possible exact duplicates
(`[(60, 120), (60, 120)]` → `[(60, 120)]`) and bookings nested in others
(`[(60, 300), (120, 180)]` → `[(60, 300)]`). Minutes are unbounded and may be
negative — the night shift renders relative to the following midnight, and
`[(-60, 0), (0, 60)]` merges to `[(-60, 60)]` like any other pair. An entry may
be a `tuple` or a `list` of exactly two `int`s; output is always tuples.

## Errors

`ValueError` if any entry has `start > end`; the message must contain the pair
rendered as `(start, end)` — `(120, 60)` for `(120, 60)` — so on-call can grep it
out of the log. Also `ValueError` if an entry isn't a two-element `tuple`/`list`
of `int`s. `start == end` is not an error, it's a cancellation, and is dropped
silently.

## Out of scope

Rooms, attendees, timezones — the function sees numbers only. Splitting blocks
that cross midnight — `(-60, 60)` is legitimate, the renderer handles it.
Persistence, caching, logging.
