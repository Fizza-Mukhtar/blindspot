# LEDGER-238 — Split a settlement amount across weighted payees without losing a cent

**Component:** `ledger/settlement`
**Reporter:** Marek (Payments Platform)
**Consumers:** the payout batcher, the refund splitter, the marketplace commission ledger

## Background

Every night the payout batcher takes one settled charge and divides it between
the parties who have a claim on it — the seller, the platform, sometimes a
referral partner or a tax authority. Today it does this with
`round(total * weight / sum(weights))` per payee. Last Thursday a €10.00 charge
split three ways paid out €10.01, the nightly reconciliation job refused to
close the book, and someone had to hand-post a one-cent correction at 02:40.

Money is not a real number and it does not divide. The fix is the classic
`allocate` operation from Martin Fowler's Money pattern
(<https://martinfowler.com/eaaCatalog/money.html>): the whole is handed out in
whole minor units, and the parts are *made* to sum back to the whole. The same
procedure is known outside finance as the largest-remainder (Hamilton)
apportionment method.

## What to build

```python
def allocate(total_cents: int, weights: list[int]) -> list[int]:
    ...
```

`total_cents` is an amount in **minor units** (cents, pence, yen — the function
neither knows nor cares which). `weights` gives the relative claim of each
payee. Return a **new** list of integers, the same length as `weights` and in
the same order, holding each payee's amount in minor units. Do not mutate the
input.

## The conservation rule

This is the whole point of the ticket, so it is stated first and it is absolute:

> `sum(allocate(total_cents, weights)) == total_cents` for **every** input the
> function accepts.

No minor unit may be created and none may be destroyed. If your arithmetic and
this identity ever disagree, the identity wins.

## How the split is computed

Let `W = sum(weights)`. For a **non-negative** `total_cents`:

1. Payee `i`'s exact claim is the rational number `total_cents * weights[i] / W`.
   Compute it exactly with integer arithmetic — `divmod(total_cents * weights[i], W)`
   is all that is needed. Do **not** route the value through binary floating
   point; `0.1 + 0.2` problems in a ledger are how this ticket got written.
2. Payee `i` provisionally receives the **floor** of that claim, and carries a
   fractional remainder equal to `(total_cents * weights[i]) mod W`, over `W`.
3. Those floors will fall short of the total by some number of minor units,
   `leftover = total_cents - sum(floors)`.
4. Hand out those `leftover` units **one each** to the payees with the
   **largest fractional remainders**, biggest remainder first. Each payee
   receives at most one extra unit; `leftover` is always strictly smaller than
   the number of payees carrying a non-zero remainder, so the units never run
   out and nobody is served twice.
5. **Ties on the fractional remainder are broken by lowest index first.** When
   two payees carry exactly the same remainder, the one earlier in `weights`
   gets the unit. This clause is not decoration — it is the only thing that
   makes the function a function rather than a family of equally defensible
   answers, and the reconciliation job diffs consecutive runs, so the output
   must be reproducible down to which payee got the odd cent.

A payee whose weight is `0` has an exact claim of `0` and a remainder of `0`,
so it receives exactly `0` — step 4 can never reach it.

### Worked example

`allocate(10, [1, 2, 4])`, so `W = 7`:

| i | weight | `10 * w` | floor (`// 7`) | remainder (`% 7`) |
|---|--------|----------|----------------|-------------------|
| 0 | 1      | 10       | 1              | 3                 |
| 1 | 2      | 20       | 2              | 6                 |
| 2 | 4      | 40       | 5              | 5                 |

The floors sum to 8, so `leftover = 2`. The two largest remainders are payee 1
(6) and payee 2 (5), so each gains one unit and payee 0 gains nothing. Result:
`[1, 3, 6]`, which sums to 10.

And the tie case: `allocate(100, [1, 1, 1])` gives floors `[33, 33, 33]` with
one unit left over and three identical remainders, so index 0 takes it —
`[34, 33, 33]`.

## Negative totals

Refund reversals and chargebacks come through this function with a negative
`total_cents`, and they must reconcile just as exactly.

**The sign is factored out before anything else happens.** Allocate
`abs(total_cents)` by the rules above, then negate every element of the result.
Equivalently, for every accepted `weights` and every integer `t`:

```python
allocate(-t, weights) == [-x for x in allocate(t, weights)]
```

So the extra unit goes to the payee who would have received the extra unit on
the corresponding positive amount — the leftover is distributed by **magnitude**,
not by numeric value. `allocate(-5, [1, 1])` is `[-3, -2]`.

Do not reach for floored division on the signed total to get there. `-5 // 2`
is `-3`, which pushes the leftover the other way and yields `[-2, -3]`; that
sums correctly but is the wrong answer, and it silently disagrees with the
positive-side allocation of the very same refund.

`allocate(0, weights)` returns all zeros.

## Errors

Raise `ValueError` — with a message that says which rule was broken — when:

- `weights` is empty;
- any weight is negative (a payee cannot hold a negative claim);
- every weight is zero, so there is no basis on which to divide.

Validation happens before any allocation, and applies whatever `total_cents`
is, including `0`.

## Out of scope

- Currencies, exponents, and rounding of major units. Everything here is a
  plain integer count of minor units.
- Rounding modes. There is exactly one defined result per input.
- Any notion of fairness across *repeated* allocations (the "carry the residue
  to next month" schemes). The function is pure and has no memory.
