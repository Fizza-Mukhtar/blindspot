# RATE-338 — Replay a token-bucket limiter over a recorded request trace

**Component:** `edge/ratelimit`
**Reporter:** Dan (Edge Platform)
**Consumers:** the quota simulator, the tariff calculator, the incident replay tool

## Background

We admit customer traffic at the edge with a token bucket. Support keeps
asking us "would this customer have been throttled on Tuesday?", and right now
the only way to answer is to redeploy the gateway with the customer's quota and
replay traffic through it. We want a pure function the simulator can call with
a recorded trace instead.

The gateway itself is not being changed by this ticket. What we need is a
faithful offline model of it, so the answers we give support match what the
gateway actually did.

Two production incidents motivate the details below, so please read the accrual
rules carefully rather than reaching for the shape you remember:

* **INC-2214.** A previous simulator rounded accrued credit down to whole
  tokens on each poll. Customers polling four times a second accrued
  `floor(0.25 * rate)` = 0 tokens every time and were reported as permanently
  throttled, which was not what the gateway did.
* **INC-2251.** A previous simulator only advanced its internal accrual clock
  when it admitted a request. Every rejection therefore left the elapsed
  interval on the books to be counted a second time by the next request, and
  the simulator reported customers as admitted when the gateway had rejected
  them.

## What to build

```python
def simulate(
    capacity: float,
    refill_per_second: float,
    requests: list[tuple[float, float]],
) -> list[bool]:
    ...
```

`capacity` is the bucket size in tokens. `refill_per_second` is the rate at
which credit accrues. `requests` is the recorded trace: each entry is
`(timestamp_seconds, cost)`, where `cost` is the number of tokens the request
would consume.

Return a list of decisions, one per request, in the same order as the trace:
`True` for admitted, `False` for rejected. Do not mutate the input.

## Model

The semantics are the classic token bucket, matching the meter that RFC 2697
specifies for its committed bucket
(<https://datatracker.ietf.org/doc/html/rfc2697>, section 2): the bucket has a
size `capacity` (the RFC calls it CBS), credit accrues at `refill_per_second`
(the RFC calls it CIR), the bucket **is initially full**, the token count is
never incremented past the bucket size, a request is admitted when the token
count covers its cost and the count is then decremented by that cost, and a
rejected request leaves the token count untouched.

We deviate from the RFC in exactly one respect, deliberately: RFC 2697 adds
credit in discrete ticks, `CIR` times per second. **We accrue continuously.**
Between two consecutive trace entries separated by `elapsed` seconds, the
bucket gains exactly `elapsed * refill_per_second` tokens — a real number, with
no flooring, rounding, truncation, or bucketing into whole tokens or whole
seconds. A gap of 40 milliseconds at 5 tokens/second accrues 0.2 tokens, and
five such gaps accrue a whole token. This is the INC-2214 rule and it is not
negotiable.

Concretely, process the trace in order, holding two pieces of state: the
current token count, and the timestamp the count was last brought up to date
("the accrual mark"). For each entry `(timestamp, cost)`:

1. Bring the bucket up to date:
   `tokens = min(capacity, tokens + (timestamp - accrual_mark) * refill_per_second)`.
2. **Advance the accrual mark to `timestamp`.** This happens for *every* entry
   in the trace, admitted or rejected alike — the passage of time is not
   contingent on the outcome of a request. This is the INC-2251 rule.
3. Decide: the request is admitted when
   `tokens + 1e-9 >= cost`, and rejected otherwise. The `1e-9` is an absolute
   slack that makes the boundary well defined in the face of floating point
   drift; a request costing exactly the credit on hand is **admitted**, not
   rejected.
4. If the request was admitted, subtract its cost:
   `tokens = max(0.0, tokens - cost)`. If it was rejected, the token count is
   left exactly as step 1 left it — a rejection consumes nothing.

The bucket starts full: before the first entry the token count is `capacity`
and the accrual mark sits at the first entry's timestamp. (Any accrual imagined
before that point is clamped away by step 1 anyway.)

A consequence of step 1 and step 3 worth calling out, because the simulator's
callers rely on it: the token count is capped at `capacity`, so a request whose
cost exceeds `capacity + 1e-9` can never be admitted no matter how long the
customer waits. It is rejected, and by step 4 it consumes nothing, so the very
next request in the trace still sees the full bucket.

## Worked example

`capacity = 10`, `refill_per_second = 1`, trace:

| # | timestamp | cost | tokens before | decision | tokens after |
|---|-----------|------|---------------|----------|--------------|
| 0 | 0.0       | 10   | 10.0          | admitted | 0.0          |
| 1 | 5.0       | 10   | 5.0           | rejected | 5.0          |
| 2 | 6.0       | 10   | 6.0           | rejected | 6.0          |
| 3 | 10.0      | 10   | 10.0          | admitted | 0.0          |

Result: `[True, False, False, True]`.

Entry 2 is the one that matters. Its accrual runs from t=5 (the rejected
entry's timestamp), not from t=0, so it gains one token rather than six and is
rejected. Entry 3 then accrues four more tokens onto the six already there,
reaching — but not exceeding — the bucket size.

## Timestamps

Timestamps are non-decreasing. Two or more entries may share a timestamp; a
burst recorded at the same instant accrues nothing between its members, so the
second entry of the burst sees whatever the first left behind.

If a timestamp is strictly less than the one before it, the trace is corrupt:
raise `ValueError`.

## Errors

Raise `ValueError` for any of the following:

* `capacity` is not a finite number greater than zero;
* `refill_per_second` is not a finite number greater than zero;
* a `cost` is negative, or is not a finite number;
* a timestamp is not a finite number;
* a timestamp is strictly less than the preceding timestamp.

A cost of exactly zero is legal and is always admitted, even against an empty
bucket.

An empty trace returns an empty list.

## Out of scope

- Multiple buckets, per-endpoint quotas, or the RFC's excess bucket and its
  yellow/red distinction. One bucket, one boolean per request.
- Any persistence of bucket state between calls. The function is pure: the same
  arguments always produce the same list.
- Wall-clock time. Every timestamp the function needs is in the trace it is
  handed.
