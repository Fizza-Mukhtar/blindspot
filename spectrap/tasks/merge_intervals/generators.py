"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the reference
on each input, and keeps the first input where they disagree.  The generator is
domain-aware on purpose: intervals drawn uniformly from a wide integer range
would essentially never share an endpoint, and endpoint coincidence is where the
half-open convention actually bites.  So starts are drawn from a small grid of
minute values and durations are drawn from a small set of grid-aligned deltas,
which makes touching pairs (``end == next start``), exact duplicates and nesting
common rather than astronomically rare.  Zero-length "cancelled" rows get a fat
~27% share of the durations, and a small ~4% slice of rows is deliberately
reversed so that a healthy minority of samples must raise ``ValueError``.
"""

from __future__ import annotations

import random

# A grid, not a range: repeated values are the point.
MINUTES = [-1440, -120, -60, -30, 0, 30, 60, 90, 120, 180, 240, 300, 540, 1380, 1440]

# Grid-aligned durations.  0 appears three times out of eleven: those are the
# collapsed cancellation rows that must be dropped before merging.
DELTAS = [0, 0, 0, 30, 30, 60, 60, 90, 120, 180, 360]

# Deltas that make a row invalid (start > end).
BAD_DELTAS = [-1, -30, -60, -1440]


def _row(rng: random.Random) -> tuple[int, int]:
    start = rng.choice(MINUTES)
    if rng.random() < 0.04:
        return (start, start + rng.choice(BAD_DELTAS))
    return (start, start + rng.choice(DELTAS))


def sample(rng: random.Random) -> tuple[tuple, dict]:
    size = rng.randint(0, 7)
    rows = [_row(rng) for _ in range(size)]
    if rows and rng.random() < 0.30:
        # Databases hand back duplicates; so should we.
        rows.append(rng.choice(rows))
        rng.shuffle(rows)
    if rows and rng.random() < 0.10:
        # Occasionally hand one row over as a list rather than a tuple.
        index = rng.randrange(len(rows))
        rows[index] = list(rows[index])  # type: ignore[call-overload]
    return (rows,), {}


# Inputs that are always tried first, before random sampling.  These encode the
# corners the ticket and the half-open convention call out by name.
SEEDS: list[tuple[tuple, dict]] = [
    (([],), {}),                                       # empty input -> empty list
    (([(60, 120)],), {}),                              # single booking survives
    (([(60, 120), (120, 180)],), {}),                  # touching -> one block
    (([(60, 120), (121, 180)],), {}),                  # one free minute -> two blocks
    (([(0, 60), (90, 90), (120, 180)],), {}),          # cancellation must not bridge
    (([(60, 60)],), {}),                               # only a cancellation -> []
    (([(0, 0), (0, 0), (1440, 1440)],), {}),           # all cancellations -> []
    (([(60, 120), (60, 120)],), {}),                   # exact duplicates
    (([(300, 360), (60, 120), (120, 180)],), {}),      # unsorted input
    (([(60, 300), (120, 180)],), {}),                  # fully nested booking
    (([(-60, 0), (0, 60)],), {}),                      # negative minutes, touching
    (([(-120, -60), (-60, -60), (-30, 0)],), {}),      # negative cancellation
    (([(0, 60), (60, 120), (120, 180), (180, 240)],), {}),  # adjacency chain
    (([(0, 60), [60, 120]],), {}),                     # a row given as a list
    (([(120, 60)],), {}),                              # invalid: ends before it starts
    (([(0, 60), (200, 100)],), {}),                    # invalid row after a valid one
]
