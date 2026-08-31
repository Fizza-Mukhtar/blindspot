# PLAT-2291 — Compute a Full Jitter retry schedule for the API client

**Component:** `platform/retry`
**Reporter:** Dan (SRE, on-call for the checkout gateway)
**Consumers:** the outbound HTTP client, the SQS consumer, the payment reconciliation worker

## Background

Last Thursday's partial outage of the payments upstream turned into a full one
because every one of our pods retried on the same exponential curve. When the
upstream came back it was immediately hit by a synchronised wall of retries and
fell over again. The AWS Architecture Blog post *Exponential Backoff And Jitter*
(<https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/>)
measured exactly this and recommends the variant it calls **Full Jitter**, which
is what we are standardising on across all our clients.

We want the schedule computed up front as plain numbers so that we can log it,
assert on it in the client's unit tests, and show it in the retry dashboard. The
function must not sleep and must not touch a clock.

## What to build

```python
def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    ...
```

Return a **new** list of `attempts` delays, in seconds. Element `i` of the list
is the delay to wait before retry attempt `i`, and attempt numbering **starts at
0**, so element `0` is the delay before the very first retry.

`rand` is injected rather than taken from the `random` module so that the
schedule stays pure and unit-testable: the client's tests pass in
`lambda upper: upper` to see the worst case and `lambda upper: 0.0` to see the
best case, and production passes in `random.uniform`-style draw. `rand(upper)`
returns a float in the closed interval `[0, upper]`. Treat it as trustworthy —
whatever it returns is the delay.

## The Full Jitter rule

For each attempt `i` (`i = 0, 1, 2, ...`):

```
ceiling_i = min(cap, base * 2**i)
delay_i   = rand(ceiling_i)
```

Three things about that formula are load-bearing and have been got wrong in our
older clients, so please read them carefully:

1. **`cap` bounds the ceiling of the random range, not the delay.** The cap is
   applied to `base * 2**i` *before* the draw. Drawing from the uncapped
   exponential range and then clamping the result to `cap` is a different (and
   worse) distribution, and is not what we are asking for.
2. **There is no additive term.** The delay is the draw and nothing but the
   draw. `base + rand(...)` and `ceiling/2 + rand(ceiling/2)` are the blog
   post's *Equal Jitter* variant, which we are explicitly not using.
3. **Attempt 0 is already jittered.** The first delay is `rand(min(cap, base))`,
   not `base`. There is no unjittered first hop.

`rand` must be called exactly once per attempt, in attempt order, with
`ceiling_i` as its single argument. Return each drawn value unchanged: do not
clamp it, round it, floor it at some minimum, or add anything to it.

## Worked example

With `base = 0.2`, `cap = 5.0`, `attempts = 6`, the ceilings are:

```
i:         0     1     2     3     4     5
base*2**i: 0.2   0.4   0.8   1.6   3.2   6.4
ceiling:   0.2   0.4   0.8   1.6   3.2   5.0     <- last one clamped by cap
```

so `schedule(6, 0.2, 5.0, lambda u: u)` is `[0.2, 0.4, 0.8, 1.6, 3.2, 5.0]`,
`schedule(6, 0.2, 5.0, lambda u: 0.0)` is six zeros, and
`schedule(6, 0.2, 5.0, lambda u: u / 2)` is `[0.1, 0.2, 0.4, 0.8, 1.6, 2.5]` —
note the last element, which is `cap/2` and not `cap`.

## Large attempt counts

The reconciliation worker retries for hours and asks for schedules of a couple
of thousand attempts. Once `base * 2**i` has reached `cap` every later ceiling is
also `cap`, so the exponent must be clamped at that point rather than evaluated:
computing `2**i` for `i` in the thousands either produces a huge integer or
overflows to infinity, and `schedule(2000, 1.0, 30.0, rand)` must return 2000
finite delays without raising. Every returned delay must be a finite number in
`[0, cap]`.

## Errors and edge cases

- `attempts == 0` returns an empty list. It is not an error.
- `attempts < 0` raises `ValueError`.
- `base` and `cap` must each be a finite number strictly greater than zero.
  Zero, negative, `inf` and `nan` all raise `ValueError` — note that `nan`
  slips through an ordinary `<= 0` check, so test for finiteness explicitly.
- `cap < base` is legitimate and common (a client that wants a flat, fully
  jittered delay sets `cap` low). Every ceiling is then `cap`, including the
  one for attempt 0. `cap == base` behaves the same way.
- Validate in the order `attempts`, then `base`, then `cap`, and make each
  `ValueError` message contain the name of the offending parameter
  (`"attempts"`, `"base"` or `"cap"`) so the log line is greppable.

## Out of scope

- Deciding *whether* to retry, classifying errors as retryable, and the deadline
  budget. Callers already do that.
- Validating that `rand` is callable or that it honours its contract.
- Sleeping, jitter for the initial request itself, and anything to do with
  circuit breaking.
