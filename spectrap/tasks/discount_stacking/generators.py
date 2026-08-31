"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the
reference on each input, and keeps the first input where they disagree.  The
space is biased on purpose.  Uniformly random money would essentially never
land on the corners where PRICING-2317 actually bites, so the generator leans
hard on:

  * subtotals whose half-cent lands exactly on a rounding tie (``x.x5``), which
    is the only place ROUND_HALF_EVEN can be told apart from ROUND_HALF_UP;
  * stacks of two to four percentages, where compounding diverges from summing;
  * mixed percent/amount stacks, where the order of application is observable;
  * fixed amounts far larger than the subtotal, to force the clamp at zero and
    then keep discounting a zero running total;
  * boundary percentages 0 and 100, and values with more than two fractional
    digits, which only matter because rounding happens at every step.

Roughly one call in seven is deliberately invalid so the error contract gets
exercised too.
"""

from __future__ import annotations

import random

# Subtotals chosen so that a 10%/50% cut lands on an exact half cent.
TIE_SUBTOTALS = [
    "0.05", "0.15", "0.25", "1.05", "1.15", "1.25", "3.05", "10.05", "10.15",
    "10.25", "0.01", "0.03", "2.55", "7.35", "19.99", "99.95", "100.05",
]
PLAIN_SUBTOTALS = [
    "0.00", "0.10", "1.00", "9.99", "12", "7.5", "100.00", "250.00", "999.99",
    "0.005", "0.015", "1234.567",
]

PERCENTS = [
    "0", "1", "5", "10", "12.5", "15", "20", "25", "33.33", "40", "50",
    "66.67", "75", "90", "99.99", "100",
]
AMOUNTS = [
    "0.00", "0.005", "0.01", "0.05", "0.50", "1.00", "2.50", "3.335", "5.00",
    "9.99", "10.00", "50.00", "100.00", "1000.00",
]

BAD_MONEY = ["", " 5.00", "+5.00", "5,000.00", "1e3", "abc", "5.", ".5", "--1", "NaN"]
BAD_KINDS = ["bogo", "PERCENT", "Percent", "fixed", "", "shipping"]


def _subtotal(rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.45:
        return rng.choice(TIE_SUBTOTALS)
    if roll < 0.75:
        return rng.choice(PLAIN_SUBTOTALS)
    # Arbitrary cent amount, built from integers so no float ever appears.
    cents = rng.randrange(0, 200_001)
    return f"{cents // 100}.{cents % 100:02d}"


def _discount(rng: random.Random) -> dict:
    if rng.random() < 0.6:
        return {"kind": "percent", "value": rng.choice(PERCENTS)}
    return {"kind": "amount", "value": rng.choice(AMOUNTS)}


def _corrupt(rng: random.Random, subtotal: str, discounts: list[dict]) -> tuple[str, list[dict]]:
    """Break exactly one thing, uniformly over the error clauses of the spec."""
    choice = rng.randrange(6)
    if choice == 0:
        return "-" + rng.choice(TIE_SUBTOTALS), discounts
    if choice == 1:
        return rng.choice(BAD_MONEY), discounts
    if not discounts:
        discounts = [_discount(rng)]
    index = rng.randrange(len(discounts))
    if choice == 2:
        discounts[index] = {"kind": rng.choice(BAD_KINDS), "value": "10"}
    elif choice == 3:
        discounts[index] = {"kind": discounts[index]["kind"], "value": "-1.00"}
    elif choice == 4:
        discounts[index] = {"kind": "percent", "value": rng.choice(["100.01", "101", "250"])}
    else:
        discounts[index] = rng.choice([{"kind": "percent"}, {"value": "10"}, {}])
    return subtotal, discounts


def sample(rng: random.Random) -> tuple[tuple, dict]:
    subtotal = _subtotal(rng)
    count = rng.choice([0, 1, 2, 2, 3, 3, 4])
    discounts = [_discount(rng) for _ in range(count)]
    if rng.random() < 0.14:
        subtotal, discounts = _corrupt(rng, subtotal, discounts)
    return (subtotal, discounts), {}


# Tried before random sampling.  Every corner the ticket names, by name.
SEEDS: list[tuple[tuple, dict]] = [
    # Percentages compound, they do not add: 20% then 10% is 28% off.
    (("100.00", [{"kind": "percent", "value": "20"}, {"kind": "percent", "value": "10"}]), {}),
    # Three compounding percentages: 51.20, not 40.00.
    (("100.00", [{"kind": "percent", "value": "20"}] * 3), {}),
    # The ticket's worked example.
    (("100.00", [{"kind": "percent", "value": "20"}, {"kind": "amount", "value": "5.00"},
                 {"kind": "percent", "value": "10"}]), {}),
    # Same stack, swapped: order of application is observable.
    (("100.00", [{"kind": "amount", "value": "5.00"}, {"kind": "percent", "value": "20"}]), {}),
    (("100.00", [{"kind": "percent", "value": "20"}, {"kind": "amount", "value": "5.00"}]), {}),
    # ROUND_HALF_EVEN ties, both directions.
    (("10.05", [{"kind": "percent", "value": "50"}]), {}),
    (("10.15", [{"kind": "percent", "value": "50"}]), {}),
    # Rounding after every step vs rounding once at the end (0.94 vs 0.93).
    (("1.15", [{"kind": "percent", "value": "10"}, {"kind": "percent", "value": "10"}]), {}),
    # Clamp at zero, then keep discounting zero.
    (("10.00", [{"kind": "amount", "value": "15.00"}, {"kind": "percent", "value": "50"}]), {}),
    (("10.00", [{"kind": "amount", "value": "15.00"}, {"kind": "amount", "value": "5.00"}]), {}),
    # Empty stack: normalise only.
    (("7.5", []), {}),
    # Boundary: 100% zeroes the line and later discounts leave it at zero.
    (("19.99", [{"kind": "percent", "value": "100"}, {"kind": "amount", "value": "1.00"}]), {}),
    # Invalid: negative subtotal, negative value, percent > 100, unknown kind.
    (("-1.00", []), {}),
    (("10.00", [{"kind": "amount", "value": "-1.00"}]), {}),
    (("10.00", [{"kind": "percent", "value": "100.01"}]), {}),
    (("10.00", [{"kind": "bogo", "value": "10"}]), {}),
]
