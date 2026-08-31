"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the
reference on each input, and keeps the first input where they disagree.  The
generator is domain-aware on purpose.  Uniformly random totals and weights
would divide cleanly far too rarely to be interesting and would essentially
never hit the corners where the largest-remainder rule bites, so the space is
biased towards:

* small totals against small weight sets, where a single leftover unit is a
  large fraction of the answer;
* equal weights, which manufacture exact remainder ties and so probe the
  lowest-index tie-break;
* weight sets containing zeros, and sets where one payee holds everything;
* totals that are exact multiples of ``sum(weights)`` (no leftover at all) and
  totals one or two units either side of such a multiple (maximum leftover);
* negative totals, at roughly the same rate as positive ones, because the sign
  rule is where implementations diverge most;
* a deliberate minority (~1 in 7) of invalid inputs that must raise ValueError.
"""

from __future__ import annotations

import random


def _weights(rng: random.Random) -> list[int]:
    """A weight vector drawn from the shapes that make the split interesting."""
    style = rng.choice(
        ["equal", "equal", "small", "small", "zeros", "one_big", "powers", "fine"]
    )
    size = rng.randint(1, 6)

    if style == "equal":
        # Identical weights force identical remainders -> tie-break territory.
        unit = rng.choice([1, 1, 2, 3, 7])
        return [unit] * size
    if style == "small":
        return [rng.randint(1, 5) for _ in range(size)]
    if style == "zeros":
        weights = [rng.choice([0, 0, 1, 2, 3]) for _ in range(size)]
        if sum(weights) == 0:  # keep it valid; all-zero is covered by SEEDS
            weights[rng.randrange(size)] = 1
        return weights
    if style == "one_big":
        weights = [rng.choice([0, 1]) for _ in range(size)]
        weights[rng.randrange(size)] = rng.choice([97, 100, 999])
        return weights
    if style == "powers":
        return [1 << k for k in range(size)]
    # "fine": near-equal large weights, where remainders cluster very closely.
    base = rng.choice([100, 1000])
    return [base + rng.randint(-3, 3) for _ in range(size)]


def _total(rng: random.Random, total_weight: int) -> int:
    """A total biased towards zero-leftover and maximum-leftover cases."""
    mode = rng.choice(
        ["tiny", "tiny", "small", "exact", "near_exact", "near_exact", "big", "zero"]
    )
    if mode == "zero":
        return 0
    if mode == "tiny":
        magnitude = rng.randint(1, 4)
    elif mode == "small":
        magnitude = rng.randint(1, 40)
    elif mode == "exact":
        magnitude = total_weight * rng.randint(1, 5)
    elif mode == "near_exact":
        magnitude = total_weight * rng.randint(1, 5) + rng.randint(-3, 3)
        magnitude = abs(magnitude)
    else:
        magnitude = rng.randint(1, 250_000)
    # Negative totals get their own generous share of the budget.
    return -magnitude if rng.random() < 0.4 else magnitude


def sample(rng: random.Random) -> tuple[tuple, dict]:
    weights = _weights(rng)
    total = _total(rng, sum(weights))

    if rng.random() < 0.14:  # a healthy minority of rejects
        kind = rng.choice(["empty", "negative", "all_zero"])
        if kind == "empty":
            weights = []
        elif kind == "all_zero":
            weights = [0] * rng.randint(1, 4)
        else:
            weights = list(weights)
            weights[rng.randrange(len(weights))] = -rng.randint(1, 9)

    return (total, weights), {}


# A handful of inputs that are always tried first, before random sampling.
# These encode the corners the SPEC and the Money pattern call out by name.
SEEDS: list[tuple[tuple, dict]] = [
    ((5, [1, 1]), {}),  # Fowler: five cents two ways is 3 and 2
    ((10, [1, 2, 4]), {}),  # the SPEC's worked example -> [1, 3, 6]
    ((100, [1, 1, 1]), {}),  # three-way tie, lowest index takes the unit
    ((5, [1, 1, 1, 1]), {}),  # four-way tie, one leftover
    ((100, [404, 397, 199]), {}),  # Hamilton apportionment -> [40, 40, 20]
    ((11, [0, 1, 1]), {}),  # zero weight receives exactly zero
    ((9, [0, 5, 0]), {}),  # one payee holds the entire claim
    ((100, [1, 1, 1, 1]), {}),  # exact division, no leftover at all
    ((0, [1, 2, 3]), {}),  # zero total
    ((7, [3]), {}),  # single payee takes everything
    ((-5, [1, 1]), {}),  # negative: mirror of [3, 2], NOT [-2, -3]
    ((-10, [1, 2, 4]), {}),  # negative form of the worked example
    ((-11, [0, 1, 1]), {}),  # negative with a zero-weight payee
    ((100, []), {}),  # invalid: empty weights
    ((100, [1, -1, 2]), {}),  # invalid: negative weight
    ((100, [0, 0, 0]), {}),  # invalid: all weights zero
]
