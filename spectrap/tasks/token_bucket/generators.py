"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the reference
on each input, and keeps the first input where they disagree.  Uniform random
traces would almost never expose the interesting behaviour: gaps drawn from a
continuous distribution essentially never land on an exact admission boundary,
and costs drawn independently of the bucket size are either trivially admitted
or trivially rejected.  So the space is biased three ways:

* **sub-second gaps** dominate the gap distribution (0.02s .. 0.5s), because
  that is where flooring or whole-second bucketing of accrued credit diverges
  from continuous accrual;
* **costs are drawn relative to the bucket**, including exactly the bucket size,
  exactly the credit the preceding gap accrued, and just over the bucket size,
  so the ``>=`` boundary and the oversized-request rule are hit constantly;
* **bursts** repeat a timestamp, and long idle gaps force the clamp at capacity.

A minority of samples are deliberately malformed (regressing timestamp,
negative cost, non-positive capacity or rate) so that the error contract is
exercised too.
"""

from __future__ import annotations

import random

CAPACITIES = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 100.0]
RATES = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]

# Sub-second gaps first, on purpose; the last two force the clamp at capacity.
GAPS = [0.0, 0.02, 0.05, 0.1, 0.1, 0.2, 0.25, 0.25, 0.4, 0.5, 0.5, 1.0, 2.0, 60.0]

START_TIMES = [0.0, 0.0, 0.0, 5.0, 1_000.0, -3.0]


def _cost(rng: random.Random, capacity: float, rate: float, gap: float) -> float:
    """Costs clustered on the boundaries the ticket calls out."""
    pick = rng.random()
    if pick < 0.20:
        return capacity  # exactly the bucket size
    if pick < 0.40:
        return round(gap * rate, 12)  # exactly what the preceding gap accrued
    if pick < 0.50:
        return round(capacity * rng.choice([0.25, 0.5, 0.75]), 12)
    if pick < 0.58:
        return capacity + rng.choice([1e-12, 0.5, 1.0])  # oversized
    if pick < 0.64:
        return 0.0
    return round(rng.choice([0.1, 0.25, 0.5, 1.0, 2.0]), 12)


def _trace(rng: random.Random, capacity: float, rate: float) -> list[tuple[float, float]]:
    length = rng.randint(0, 12)
    now = rng.choice(START_TIMES)
    trace: list[tuple[float, float]] = []
    for _ in range(length):
        # A quarter of the entries repeat the previous timestamp (a burst).
        gap = 0.0 if (trace and rng.random() < 0.25) else rng.choice(GAPS)
        now = round(now + gap, 12)
        trace.append((now, _cost(rng, capacity, rate, gap)))
    return trace


def sample(rng: random.Random) -> tuple[tuple, dict]:
    capacity = rng.choice(CAPACITIES)
    rate = rng.choice(RATES)
    trace = _trace(rng, capacity, rate)

    corrupt = rng.random()
    if corrupt < 0.05 and len(trace) >= 2:
        # Regressing timestamp: the trace is corrupt and must be rejected.
        index = rng.randrange(1, len(trace))
        timestamp, cost = trace[index]
        trace[index] = (timestamp - rng.choice([0.001, 1.0, 5.0]), cost)
    elif corrupt < 0.09 and trace:
        index = rng.randrange(len(trace))
        timestamp, _ = trace[index]
        trace[index] = (timestamp, -rng.choice([1e-9, 0.5, 3.0]))
    elif corrupt < 0.11:
        capacity = rng.choice([0.0, -1.0])
    elif corrupt < 0.13:
        rate = rng.choice([0.0, -2.5])

    return (capacity, rate, trace), {}


# Inputs that are always tried first, before random sampling.  Between them they
# cover every corner the ticket and RFC 2697 name explicitly.
SEEDS: list[tuple[tuple, dict]] = [
    # Empty trace.
    ((1.0, 1.0, []), {}),
    # Bucket starts full: the very first request may spend the whole bucket.
    ((5.0, 1.0, [(0.0, 5.0)]), {}),
    # The worked example: the accrual mark advances across a rejection.
    ((10.0, 1.0, [(0.0, 10.0), (5.0, 10.0), (6.0, 10.0), (10.0, 10.0)]), {}),
    # Continuous fractional accrual at 100ms polls -- flooring starves this.
    (
        (
            1.0,
            1.0,
            [(0.0, 1.0), (0.1, 0.1), (0.2, 0.1), (0.3, 0.1), (0.4, 0.1), (0.5, 0.1)],
        ),
        {},
    ),
    # Sub-second gap at a fractional rate: 0.1s * 3/s = 0.3 tokens.
    ((1.0, 3.0, [(0.0, 1.0), (0.1, 0.3), (0.1, 0.3)]), {}),
    # Long idle: credit is clamped at capacity, never above it.
    ((5.0, 10.0, [(0.0, 5.0), (100.0, 5.0), (100.0, 1.0)]), {}),
    # Oversized cost: never admitted, and consumes nothing.
    ((5.0, 1.0, [(0.0, 6.0), (0.0, 5.0)]), {}),
    # Cost exactly equal to the credit on hand is admitted.
    ((2.0, 1.0, [(0.0, 2.0), (1.0, 1.0), (1.5, 0.5)]), {}),
    # A hair over the credit on hand is rejected.
    ((2.0, 1.0, [(0.0, 2.0), (1.0, 1.5)]), {}),
    # Burst at a single timestamp: no accrual between members.
    ((3.0, 1.0, [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]), {}),
    # Zero cost is admitted even against an empty bucket.
    ((1.0, 1.0, [(0.0, 1.0), (0.0, 0.0)]), {}),
    # Rejection consumes nothing: the smaller request behind it still fits.
    ((5.0, 1.0, [(0.0, 4.0), (0.0, 2.0), (0.0, 1.0)]), {}),
    # Invalid: regressing timestamp.
    ((1.0, 1.0, [(1.0, 0.5), (0.5, 0.5)]), {}),
    # Invalid: negative cost.
    ((1.0, 1.0, [(0.0, -0.25)]), {}),
    # Invalid: non-positive capacity.
    ((0.0, 1.0, [(0.0, 0.0)]), {}),
    # Invalid: non-positive refill rate.
    ((1.0, -2.0, [(0.0, 0.5)]), {}),
]
