# FLAG-238 — Consistent percentage rollout for feature flags

**Component:** `platform/flagd/bucketing`
**Reporter:** Marcus (Growth Platform)
**Consumers:** edge workers, the batch recommendation job, the mobile BFF, analytics

## Background

Last week's `checkout-v2` ramp bounced users between the new and old checkout
between requests, losing carts. Two causes: the edge worker bucketed on the
builtin `hash()`, salted per process unless `PYTHONHASHSEED` is pinned
(<https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED>), so each
process placed a user differently and the exposure logger disagreed with the
edge about who had seen the feature; and the batch job folded the percentage
into the hash to "re-randomise the cohort" each step, reshuffling everyone
instead of widening one fixed ordering
(<https://www.getunleash.io/blog/hashing-it-right-solving-a-gradual-rollout-puzzle>).
Both call sites are being replaced with one shared function.

## What to build

```python
def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    ...
```

`True` when this user is inside the rollout for this flag at this percentage.
Pure: same arguments, same answer, in any process, on any machine, in any Python
build. Returns an actual `bool`.

Each `(flag_key, user_id)` pair belongs to one of 100 buckets numbered `0`–`99`.
Join the two identifiers with a single ASCII colon, encode UTF-8, take the
SHA-256 digest, read it as one unsigned big-endian integer and reduce modulo
100; the user is enabled when the bucket is strictly less than `percentage` —

```python
bucket = int(hashlib.sha256(f"{flag_key}:{user_id}".encode("utf-8")).hexdigest(), 16) % 100
```

The material is the two identifiers and the colon between them and nothing else,
no salt, no namespace and not the percentage, since a user in the rollout at one
percentage has to still be in at every higher one and a ramp may only add users,
never drop one. SHA-256 rather than `hash()` or any other digest — the Go and
TypeScript SDKs run the same line and must agree with us byte for byte. As a
check, `"checkout-v2:user-1042"` is bucket 19: off at 19, on at 20. At the
ends, `0` disables everyone (nothing is `< 0`) and `100` enables
everyone (every bucket `0`–`99` is `< 100`), so nobody stays dark at full
rollout.

## Errors

Types before range. A non-`str` `flag_key` or `user_id` raises `TypeError`, as
does a `percentage` that is not an `int` — floats included, even integral ones
like `50.0`, and `bool` included, since `True`/`False` satisfy
`isinstance(x, int)` but are not percentages. An `int` percentage outside the
inclusive `0`–`100` range raises `ValueError`. Types first means
`is_enabled("f", "u", 101.0)` is a `TypeError`, not a `ValueError`. Nothing else
is rejected: empty identifiers are legitimate (the analytics job evaluates
anonymous sessions, whose user id is empty) and hash like any other string, and
non-ASCII identifiers are covered by the UTF-8 step.

## Out of scope

Attribute targeting, allow-lists and per-environment overrides (the caller
resolves those first), sticky QA overrides, and any I/O, caching or logging —
no clock, no random source, no config.
