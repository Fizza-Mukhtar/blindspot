# RATE-338 — Replay a token-bucket limiter over a recorded request trace

**Component:** `edge/ratelimit`
**Reporter:** Dan (Edge Platform)
**Consumers:** the quota simulator, the tariff calculator, the incident replay tool

## Background

Support keeps asking whether a customer would have been throttled on a given
day, and answering means redeploying the gateway with their quota and replaying
traffic through it. We want a pure function the simulator can call with a
recorded trace instead — a faithful offline model of the gateway, which this
ticket leaves alone.

## What to build

```python
def simulate(
    capacity: float,
    refill_per_second: float,
    requests: list[tuple[float, float]],
) -> list[bool]:
    ...
```

`capacity` is the bucket size in tokens, `refill_per_second` the rate at which
credit accrues, `requests` the recorded trace of `(timestamp_seconds, cost)`
pairs. Return one decision per request in trace order, `True` admitted and
`False` rejected. Do not mutate the input; an empty trace returns an empty list.

## Model

Classic token bucket, semantics as in the committed bucket of RFC 2697 section 2
(<https://datatracker.ietf.org/doc/html/rfc2697>): size `capacity` (the RFC's
CBS), credit accruing at `refill_per_second` (CIR), bucket initially full, count
never incremented past the bucket size, a request admitted when the count covers
its cost and the count then decremented by it, a rejected request leaving the
count untouched. We deviate deliberately in one respect: where the RFC adds
credit in discrete ticks, we accrue continuously, so between trace entries
`elapsed` seconds apart the bucket gains exactly `elapsed * refill_per_second`
tokens as a real number, with no flooring, rounding, truncation or bucketing
into whole tokens or whole seconds. A 40 ms gap at 5 tokens/second is worth
0.2 tokens, and five such gaps a whole token.

Concretely, carry a token count starting at `capacity` and a mark for the
timestamp that count was last brought up to date, starting at the first entry's
timestamp. Per entry, first accrue —
`tokens = min(capacity, tokens + (timestamp - mark) * refill_per_second)` — and
move the mark to `timestamp`, which happens for every entry in the trace
regardless of whether the request is admitted or rejected. Then admit when
`tokens + 1e-9 >= cost`, an absolute slack against floating-point drift, so a
cost equal to the credit on hand is admitted; on admission set
`tokens = max(0.0, tokens - cost)`. A rejection consumes nothing and leaves the
count as the accrual step left it, which with the cap at `capacity` means a cost
above `capacity + 1e-9` is never admitted however long the customer waits, and
the entry behind it still sees the bucket it would otherwise have seen.

Timestamps are non-decreasing, and entries may share one: a burst recorded at
the same instant accrues nothing between its members, so its second entry sees
whatever the first left behind.

## Errors

`ValueError` if `capacity` or `refill_per_second` is not a finite number greater
than zero, if a cost is negative or is not a finite number, if a timestamp is
not a finite number, or if a timestamp is strictly less than the one before it —
that last means the trace is corrupt. A cost of exactly zero is legal and is
always admitted, even against an empty bucket.

## Out of scope

- More than one bucket, per-endpoint quotas, the RFC's excess bucket and its
  yellow/red distinction. One bucket, one boolean per request.
- Persistence of bucket state between calls: the function is pure.
- Wall-clock time; every timestamp the function needs is in the trace.
