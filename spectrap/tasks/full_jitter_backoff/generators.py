"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the reference
on each input, and keeps the first input where they disagree.  The generator is
domain-aware on purpose.

Two biases matter here.  First, the injected ``rand`` is always a *pure*
function of its argument (``lambda upper: upper * fraction``) rather than a
stateful draw: the same callable object is handed to both implementations, so a
stateful one would advance its stream between the two runs and manufacture fake
disagreements.  The fractions are weighted towards 0.0 and 1.0, which are the
two settings that expose the additive-term and clamp-after-draw mistakes.

Second, ``base``/``cap`` pairs are chosen so that the ceiling actually reaches
``cap`` inside the requested number of attempts (uniform random floats would
usually either cap on attempt 0 or never cap at all), with ``cap < base`` and
``cap == base`` over-represented, plus a slice of very large attempt counts that
break a literal ``2 ** attempt``, and a minority of invalid arguments.
"""

from __future__ import annotations

import math
import random

FRACTIONS = [0.0, 1.0, 0.5, 0.25, 0.75, 1e-9, 0.9999999]
BASES = [1e-6, 0.001, 0.01, 0.1, 0.2, 0.5, 1.0, 2.0, 30.0, 1000.0, 1e-300]
CAPS = [0.05, 0.2, 1.0, 5.0, 20.0, 30.0, 1000.0, 1e300]
BIG_ATTEMPTS = [64, 200, 1100, 2100]
BAD_BOUNDS = [0.0, -0.0, -1.0, -1e-9, float("inf"), float("-inf"), float("nan")]


def _make_rand(fraction: float):
    """A deterministic, stateless draw that always returns ``fraction * upper``."""

    def rand(upper: float) -> float:
        return upper * fraction

    return rand


def sample(rng: random.Random) -> tuple[tuple, dict]:
    roll = rng.random()
    if roll < 0.05:
        attempts = rng.randint(-4, -1)  # invalid
    elif roll < 0.12:
        attempts = rng.choice(BIG_ATTEMPTS)
    elif roll < 0.22:
        attempts = rng.choice([0, 1, 2])
    else:
        attempts = rng.randint(0, 12)

    base = rng.choice(BASES)
    cap_roll = rng.random()
    if cap_roll < 0.12:
        cap = base  # cap == base: every ceiling is cap
    elif cap_roll < 0.30:
        cap = base * rng.choice([0.25, 0.5, 0.9])  # cap < base
    else:
        cap = rng.choice(CAPS)

    if rng.random() < 0.06:
        base = rng.choice(BAD_BOUNDS)
    if rng.random() < 0.06:
        cap = rng.choice(BAD_BOUNDS)

    return (attempts, base, cap, _make_rand(rng.choice(FRACTIONS))), {}


def equals(a, b) -> bool:
    """Tolerant comparison for the returned float lists."""
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
        return False
    for x, y in zip(a, b):
        try:
            fx, fy = float(x), float(y)
        except (TypeError, ValueError):
            return False
        if not math.isclose(fx, fy, rel_tol=1e-12, abs_tol=0.0):
            return False
    return True


_MAX = _make_rand(1.0)
_ZERO = _make_rand(0.0)
_HALF = _make_rand(0.5)
_QUARTER = _make_rand(0.25)

# Inputs that are always tried first, before random sampling.  These encode the
# corners the blog post and the ticket call out by name.
SEEDS: list[tuple[tuple, dict]] = [
    ((0, 1.0, 10.0, _MAX), {}),                     # attempts == 0 -> []
    ((1, 1.0, 10.0, _MAX), {}),                     # attempt 0 ceiling is min(cap, base)
    ((1, 1.0, 10.0, _ZERO), {}),                    # attempt 0 is already jittered
    ((6, 1.0, 10.0, _MAX), {}),                     # ceiling sequence, capped at i=4
    ((6, 1.0, 10.0, _HALF), {}),                    # cap bounds the ceiling, not the draw
    ((8, 0.2, 5.0, _QUARTER), {}),                  # the ticket's worked example, quartered
    ((5, 10.0, 2.0, _MAX), {}),                     # cap < base -> flat schedule
    ((4, 3.0, 3.0, _MAX), {}),                      # cap == base
    ((1500, 1.0, 30.0, _MAX), {}),                  # would overflow a literal 2**attempt
    ((3, 1e-300, 1e300, _MAX), {}),                 # ceiling nowhere near cap
    ((-1, 1.0, 10.0, _MAX), {}),                    # invalid: negative attempts
    ((3, 0.0, 10.0, _MAX), {}),                     # invalid: base == 0
    ((3, -1.0, 10.0, _MAX), {}),                    # invalid: negative base
    ((3, 1.0, 0.0, _MAX), {}),                      # invalid: cap == 0
    ((3, float("nan"), 10.0, _MAX), {}),            # invalid: nan slips past `<= 0`
    ((3, 1.0, float("inf"), _MAX), {}),             # invalid: non-finite cap
]
