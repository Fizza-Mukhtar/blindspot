# LEDGER-238 — Split a settlement amount across weighted payees without losing a cent

**Component:** `ledger/settlement`
**Reporter:** Marek (Payments Platform)

## Background

The nightly payout batcher splits each settled charge between the parties with a
claim on it using `round(total * weight / sum(weights))`. Last Thursday a €10.00
charge split three ways paid out €10.01 and reconciliation refused to close the
book. We want the `allocate` operation from Fowler's Money pattern
(<https://martinfowler.com/eaaCatalog/money.html>) — equivalently the
largest-remainder (Hamilton) apportionment method.

## What to build

```python
def allocate(total_cents: int, weights: list[int]) -> list[int]:
    ...
```

`total_cents` is an amount in minor units and `weights` gives each payee's
relative claim. Return a new list of integers, same length as `weights` and in
the same order, without mutating the input.
`sum(allocate(total_cents, weights)) == total_cents` must hold for every input
the function accepts; where that identity and your arithmetic disagree, the
identity wins.

With `W = sum(weights)`, payee `i`'s exact claim is `total_cents * weights[i] / W`;
compute it with integer arithmetic (`divmod(total_cents * weights[i], W)`), not
through binary floating point. Each payee provisionally takes the floor of that
claim and carries a fractional remainder of `(total_cents * weights[i]) % W`
over `W`. The floors fall short of the total by
`leftover = total_cents - sum(floors)` units, handed out one each to the payees
holding the largest remainders, biggest remainder first, and where two payees
carry exactly the same remainder the earlier index takes the unit —
reconciliation diffs consecutive runs, so the odd cent has to land on the same
payee every time. No payee gains more than one extra unit, and the leftover is
always smaller than the number of payees with a non-zero remainder, so the units
never run out. A weight of `0` gives an exact claim and remainder of `0`, so
that payee receives exactly `0`. So `allocate(10, [1, 2, 4])` is `[1, 3, 6]`:
floors `[1, 2, 5]`, remainders 3/7, 6/7 and 5/7, two units to place, payees 1
and 2 take one each and payee 0 gains nothing.

Refund reversals and chargebacks arrive with a negative `total_cents` and must
reconcile just as exactly. The sign is factored out before anything else:
allocate `abs(total_cents)` by the rules above and negate every element, so
`allocate(-t, weights) == [-x for x in allocate(t, weights)]` and the leftover
follows magnitude rather than numeric value. That makes `allocate(-5, [1, 1])`
equal `[-3, -2]`, not the `[-2, -3]` floored division on the signed total gives.
`allocate(0, weights)` is all zeros.

## Errors

Raise `ValueError`, with a message saying which rule was broken, when `weights`
is empty, when any weight is negative, or when every weight is zero, leaving no
basis to divide on. Validation happens before any allocation and applies
whatever `total_cents` is, including `0`.

## Out of scope

- Currencies, exponents, major-unit rounding: this is a plain integer count of
  minor units.
- Rounding modes. There is exactly one defined result per input.
- Fairness across *repeated* allocations. The function is pure, with no memory.
