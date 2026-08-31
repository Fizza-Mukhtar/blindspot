"""Reference implementation for LEDGER-238 (weighted allocation of minor units).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: Martin Fowler, *Patterns of Enterprise Application Architecture*,
the Money pattern and its ``allocate`` operation --
https://martinfowler.com/eaaCatalog/money.html.  The remainder rule is the
largest-remainder (Hamilton) apportionment method: floor every exact share,
then hand the shortfall out one unit at a time, largest fractional remainder
first.  Fowler's motivating case is that five cents split two ways must be
three and two, never two and two.
"""

from __future__ import annotations


def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """Split ``total_cents`` minor units across ``weights``, losing nothing.

    Postcondition: ``sum(result) == total_cents`` and ``len(result) == len(weights)``.
    """
    # --- Validation, before any arithmetic and regardless of total_cents. ---
    if len(weights) == 0:
        raise ValueError("weights must contain at least one payee")
    for index, weight in enumerate(weights):
        if weight < 0:
            raise ValueError(f"weight at index {index} is negative: {weight}")
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("weights must not all be zero: nothing to divide by")

    # --- The sign is factored out first (SPEC, "Negative totals"). ---------
    # Everything below allocates the magnitude; the sign is reapplied at the
    # end, so allocate(-t, w) is exactly the elementwise negation of
    # allocate(t, w).  Using floored division on a signed total would push the
    # leftover unit to the opposite payee.
    negative = total_cents < 0
    magnitude = -total_cents if negative else total_cents

    # --- Exact rational shares, floored, with their remainders kept. -------
    # Share i is magnitude * weights[i] / total_weight.  divmod on integers
    # gives the floor and the remainder numerator with no float rounding.
    floors: list[int] = []
    remainders: list[int] = []
    for weight in weights:
        quotient, remainder = divmod(magnitude * weight, total_weight)
        floors.append(quotient)
        remainders.append(remainder)

    # --- Largest remainder first, ties by lowest index. --------------------
    # leftover is provably < the number of payees with a non-zero remainder
    # (each remainder is at most total_weight - 1), so a payee with weight 0 --
    # and therefore remainder 0 -- can never be reached here, and no payee is
    # served twice.
    leftover = magnitude - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for index in order[:leftover]:
        floors[index] += 1

    if negative:
        return [-amount for amount in floors]
    return floors
