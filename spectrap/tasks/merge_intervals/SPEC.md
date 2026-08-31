# SCHED-207 — Coalesce a room's booking intervals into busy blocks

**Component:** `scheduling/calendar`
**Reporter:** Marcus (Scheduling Platform)
**Consumers:** the free/busy endpoint, the room-utilisation report, the double-booking guard

## Background

The room calendar stores one row per reservation. The free/busy endpoint has to
answer "when is this room busy?", and right now it answers with the raw rows, so
a room booked 09:00–10:00 and then 10:00–10:30 shows up as *two* busy blocks
with a phantom gap between them. Sales then see a "free" slot at 10:00 that
isn't free, book it, and we get a support ticket.

There is a second, uglier symptom. When someone cancels a reservation our
booking service does not delete the row — it collapses it, so a cancelled 10:15
meeting is persisted as the interval `(615, 615)`. Those collapsed rows are
leaking into the free/busy response as zero-width busy blocks, which the mobile
client renders as a 1px black sliver on the timeline.

We want one function that takes the raw rows and returns the room's real busy
blocks.

## What to build

```python
def merge_bookings(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    ...
```

Return a **new** list of `(start, end)` tuples. Do not mutate the input list or
any entry in it.

## The interval convention

Every booking is a **half-open** interval `[start, end)` measured in whole
minutes since midnight: the start minute is part of the booking and the end
minute is **not**. This is the convention Dijkstra argues for in EWD 831,
"Why numbering should start at zero"
(<https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD831.html>), and it is
the convention the whole scheduling stack already uses, so please keep it.

Two consequences follow directly from it, and both of them are the actual point
of this ticket:

1. **Touching bookings are contiguous, not merely close.** `[60, 120)` and
   `[120, 180)` share no minute — minute 120 belongs only to the second — yet
   there is no free minute anywhere between them. They describe one continuous
   busy stretch and must come back as the single block `[60, 180)`. A block
   boundary in the output must always mean there is at least one genuinely free
   minute on the other side of it, so `[60, 120)` and `[121, 180)` stay separate:
   minute 120 is free.

2. **A booking with `start == end` is empty.** Under the half-open convention
   `[615, 615)` contains no minutes at all; it is the collapsed row left behind
   by a cancellation. Every such entry must be **discarded before any merging
   happens**. It must never appear in the output, and — because it occupies no
   time — it must never join two blocks together. Given
   `[(0, 60), (90, 90), (120, 180)]` the answer is `[(0, 60), (120, 180)]`: the
   room is genuinely free from minute 60 to minute 120, and the cancelled 90
   does nothing to change that. If every entry is zero-length, the result is the
   empty list.

## Rules for the result

- Sorted **ascending by start**.
- Pairwise disjoint *and* pairwise non-touching: for consecutive output blocks
  `(a1, b1)` and `(a2, b2)`, `b1 < a2` strictly. No output block is zero-length.
- Every minute that is covered by at least one non-empty input booking is
  covered by exactly one output block, and no other minute is covered.
- Entries are plain `tuple` objects of two `int`s, in that order.

## Rules for the input

The input arrives straight out of a database cursor, so:

- It may be in **any order**. Do not assume it is sorted by start.
- It may contain **exact duplicates**; `[(60, 120), (60, 120)]` is one busy
  block, `[(60, 120)]`.
- It may contain bookings **nested inside** others; `[(60, 300), (120, 180)]` is
  `[(60, 300)]`.
- Minute values **may be negative**. The night shift's calendar is rendered
  relative to the following midnight, so a booking that ran 23:00–00:30 the
  previous evening is stored as `(-60, 30)`, and `[(-60, 0), (0, 60)]` merges to
  `[(-60, 60)]` like any other touching pair. There is no upper or lower bound
  on a minute value.
- An entry may be a `tuple` or a `list` of exactly two `int`s. Both are
  accepted; the output is always tuples.

An **empty input list returns an empty list**.

## Errors

Raise `ValueError` if:

- any entry has `start > end`. The message must contain the offending pair
  rendered as `(start, end)` — for `(120, 60)` the message must contain the
  substring `(120, 60)`, so on-call can grep the row out of the log; or
- any entry is not a two-element `tuple` or `list`, or either of its two
  elements is not an `int`.

Note that `start == end` is **not** an error. It is a cancellation and is
silently dropped, per the section above.

## Worked example

```python
merge_bookings([(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)])
```

Drop `(630, 630)` — cancelled. Sorted, the survivors are `(480, 540)`,
`(540, 600)`, `(600, 630)`, `(690, 700)`, `(700, 720)`. The first three touch
end-to-start and collapse into `(480, 630)`; `(690, 700)` and `(700, 720)` touch
and collapse into `(690, 720)`; minutes 630 through 689 are genuinely free, so
the two blocks stay apart:

```python
[(480, 630), (690, 720)]
```

## Out of scope

- Anything to do with which room, attendee or timezone a booking belongs to.
  The function sees numbers only.
- Splitting blocks that cross midnight. A block may legitimately span
  `(-60, 60)`; the renderer deals with that.
- Persistence, caching or logging. The function is pure.
