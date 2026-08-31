# PLAT-2291 — Compute a Full Jitter retry schedule for the API client

**Component:** `platform/retry`
**Reporter:** Dan (SRE, on-call for the checkout gateway)

## Background

Thursday's partial outage of the payments upstream went full because every pod
retried on the same exponential curve and hit it with a synchronised wall the
moment it came back. We are standardising the outbound HTTP client, the SQS
consumer and the reconciliation worker on the Full Jitter variant from the AWS
Architecture Blog's *Exponential Backoff And Jitter*
(<https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/>),
computed up front as plain numbers we can log and chart. No sleeping, no clock.

## What to build

```python
def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    ...
```

A new list of `attempts` delays in seconds, element `i` the wait before retry
attempt `i`, numbering from zero. `rand` is injected to keep this pure:
`rand(upper)` returns a float in `[0, upper]`; tests pass `lambda u: u` and
`lambda u: 0.0` for worst and best case, production a `random.uniform`-style
draw. Trust it — what it returns is the delay, handed back unchanged, not
clamped, rounded, floored at a minimum or added to.

Delays are the post's Full Jitter formula,
`sleep = random_between(0, min(cap, base * 2 ** attempt))`: one `rand` call per
attempt, in attempt order, its single argument the ceiling
`min(cap, base * 2**i)`. The cap belongs to the ceiling we hand `rand` rather
than to what comes back, and nothing is added to the draw, so attempt 0's wait
is `rand(min(cap, base))` and not a flat first hop of `base`. With `base = 0.2`,
`cap = 5.0`, `attempts = 6` the ceilings run `0.2, 0.4, 0.8, 1.6, 3.2, 5.0` (the
last clamped down from 6.4), so a `lambda u: u / 2` draw gives
`[0.1, 0.2, 0.4, 0.8, 1.6, 2.5]` — note the `cap/2` at the end.

The reconciliation worker asks for a couple of thousand attempts, so clamp the
exponent once `base * 2**i` has reached `cap` instead of evaluating `2**i` for
`i` in the thousands and getting a huge integer or an overflow to infinity:
`schedule(2000, 1.0, 30.0, rand)` returns 2000 delays without raising, each a
finite number in `[0, cap]`.

## Errors and edge cases

`attempts == 0` gives an empty list and is not an error; `attempts < 0` raises
`ValueError`. `base` and `cap` must each be finite and strictly greater than
zero — zero, negative, `inf` and `nan` all raise, and `nan` slips through a
plain `<= 0` check, so test finiteness explicitly. A `cap` at or below `base` is
legitimate and common (a client wanting a flat, fully jittered delay sets `cap`
low); every ceiling is then `cap`, attempt 0's included. Validate `attempts`,
then `base`, then `cap`, naming the offending parameter in the message so the
log line is greppable.

## Out of scope

- Whether to retry, error classification, the deadline budget: callers do that.
- Checking that `rand` is callable or honours its contract.
- Sleeping, jitter for the initial request, circuit breaking.
