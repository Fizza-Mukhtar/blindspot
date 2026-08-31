"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the reference
on each input, and keeps the first input where they disagree.  The generator is
domain-aware on purpose.

The bias that matters: ``created_at`` values are drawn from a *tiny* pool, so
almost every generated feed has several rows sharing a timestamp, and cursors
are usually taken from a real row of that feed.  Uniform random timestamps would
make ties vanishingly rare and the page boundary would never land inside a
group of rows stamped with the same second -- which is exactly the region where
a cursor that carries only ``created_at`` diverges from one that carries the
full ``(created_at, id)`` key.  Limits are kept small for the same reason: a
limit of 2 or 3 over a 10-row feed puts a boundary inside a tie group often.

A minority of samples are invalid on purpose (malformed cursors, limits below
1) so that the error contract is fuzzed too.
"""

from __future__ import annotations

import random

# Heavily repeated timestamps: the pool is small and weighted, so ties are the
# norm rather than the exception.
TIMESTAMPS = [1000, 1000, 1000, 1001, 1001, 1002, 1002, 1002, 1002, 1003]

# Payload keys that must survive the round trip untouched.
PAYLOADS = [
    {},
    {"kind": "comment"},
    {"kind": "follow", "actor": "ana"},
    {"body": "", "seen": False},
]

MALFORMED_CURSORS = [
    "",
    "1000",
    "1000:",
    ":7",
    "1000:7:1",
    "1000 : 7",
    " 1000:7",
    "-1:7",
    "1000:-7",
    "1e3:7",
    "1000;7",
    "1000:7\n",
    "abc:7",
    "1000:x",
]


def _feed(rng: random.Random) -> list[dict]:
    size = rng.randint(0, 12)
    ids = rng.sample(range(1, 60), size)
    rows = []
    for row_id in ids:
        row = {"id": row_id, "created_at": rng.choice(TIMESTAMPS)}
        row.update(rng.choice(PAYLOADS))
        rows.append(row)
    rng.shuffle(rows)  # the ticket says rows arrive unordered
    return rows


def _cursor(rng: random.Random, rows: list[dict]) -> str | None:
    roll = rng.random()
    if not rows:
        # Nothing to point at: first page, an arbitrary position, or garbage.
        if roll < 0.60:
            return None
        if roll < 0.84:
            return f"{rng.choice(TIMESTAMPS)}:{rng.randint(1, 40)}"
        return rng.choice(MALFORMED_CURSORS)
    if roll < 0.16:
        return None  # first page
    if roll < 0.62:
        # A cursor taken from a real row -- the common case, and the one that
        # lands mid-tie-group.
        row = rng.choice(rows)
        return f"{row['created_at']}:{row['id']}"
    if roll < 0.74:
        # A cursor whose row has since been deleted: real timestamp, id that is
        # not in the feed.  Position, not lookup.
        row = rng.choice(rows)
        live = {r["id"] for r in rows}
        ghost = next(i for i in range(1, 200) if i not in live)
        return f"{row['created_at']}:{ghost}"
    if roll < 0.84:
        # Off the ends of the feed entirely.
        if rng.random() < 0.5:
            return f"{min(r['created_at'] for r in rows) - 1}:1"
        return f"{max(r['created_at'] for r in rows) + 1}:1"
    return rng.choice(MALFORMED_CURSORS)


def sample(rng: random.Random) -> tuple[tuple, dict]:
    rows = _feed(rng)
    cursor = _cursor(rng, rows)
    roll = rng.random()
    if roll < 0.08:
        limit = rng.choice([0, -1, -4])
    elif roll < 0.92:
        limit = rng.randint(1, 4)
    else:
        limit = rng.randint(5, 15)
    return (rows, cursor, limit), {}


# Inputs that are always tried first, before random sampling.  Between them
# these hit every corner the ticket names: unordered input, a boundary inside a
# tie group, a cursor for a deleted row, a page that lands exactly on the last
# row, an exhausted cursor, an empty feed, and both error cases.
_TIE_FEED = [
    {"id": 4, "created_at": 300},
    {"id": 9, "created_at": 200},
    {"id": 7, "created_at": 200},
    {"id": 2, "created_at": 200},
    {"id": 5, "created_at": 100},
]

SEEDS: list[tuple[tuple, dict]] = [
    (([], None, 3), {}),                          # empty feed
    (([], "200:9", 3), {}),                       # empty feed, with a cursor
    ((list(_TIE_FEED), None, 2), {}),             # page 1, boundary inside the 200s
    ((list(_TIE_FEED), "200:9", 2), {}),          # page 2: ids 7 and 2 are still owed
    ((list(_TIE_FEED), "200:2", 2), {}),          # page 3 exhausts -> next_cursor None
    ((list(_TIE_FEED), "100:5", 2), {}),          # cursor past the end -> ([], None)
    ((list(_TIE_FEED), "200:8", 3), {}),          # cursor for a row that never existed
    ((list(_TIE_FEED), None, 5), {}),             # limit exactly the feed size
    ((list(_TIE_FEED), None, 99), {}),            # limit larger than the feed
    ((list(_TIE_FEED), None, 1), {}),             # smallest legal limit
    (([{"id": 3, "created_at": 7, "kind": "x"}], None, 4), {}),  # payload passthrough
    ((list(_TIE_FEED), "0:1", 2), {}),            # position below every row
    ((list(_TIE_FEED), None, 0), {}),             # invalid: limit below 1
    ((list(_TIE_FEED), None, -2), {}),            # invalid: negative limit
    ((list(_TIE_FEED), "200", 2), {}),            # invalid: cursor lacks the id half
    ((list(_TIE_FEED), "200:9:1", 2), {}),        # invalid: too many components
]
