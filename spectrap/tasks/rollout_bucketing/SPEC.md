# FLAG-238 — Consistent percentage rollout for feature flags

**Component:** `platform/flagd/bucketing`
**Reporter:** Marcus (Growth Platform)
**Consumers:** the API edge workers, the batch recommendation job, the mobile BFF, the analytics exposure logger

## Background

We ship every risky change behind a percentage rollout: the flag starts at 1%,
and we widen it over the course of a day or two while we watch the error
budget. Last week's `checkout-v2` ramp went badly. Support saw users complete a
purchase on the new checkout, get bounced back to the old one on their next
request, and lose their cart. Two separate causes came out of the postmortem.

The first is that the edge worker used Python's builtin `hash()` on the user id.
`hash()` is salted with a per-process random seed unless `PYTHONHASHSEED` is
pinned (see
<https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED>), so every
worker process placed the same user in a different bucket, and a user's
experience flapped depending on which process answered the request. The
analytics exposure logger — a completely separate service — disagreed with the
edge on who had even seen the feature, so the experiment readout was garbage.

The second is that the batch job mixed the current percentage into the hash so
that "each ramp step re-randomises the cohort". That reshuffles everyone at
every step: a user in the 1% cohort was very likely *not* in the 5% cohort. A
gradual rollout has to be a monotonic widening of one fixed ordering, exactly as
described in
<https://www.getunleash.io/blog/hashing-it-right-solving-a-gradual-rollout-puzzle>.

We are replacing both call sites with one shared function.

## What to build

```python
def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    ...
```

Return `True` if this user is inside the rollout for this flag at this
percentage, `False` otherwise. The function is pure: same arguments, same
answer, in any process, on any machine, in any Python build, forever. The
returned value must be an actual `bool`.

## The bucketing rule

Every `(flag_key, user_id)` pair is assigned to one of 100 buckets numbered
`0`–`99`. The assignment is pinned exactly, because three different services in
two different languages have to agree on it byte for byte:

1. Build the hash material by joining the two identifiers with a single ASCII
   colon: `f"{flag_key}:{user_id}"`. Nothing else — no flag id, no salt, no
   namespace, and **no percentage**.
2. Encode that string as **UTF-8**.
3. Take its **SHA-256** digest, read the digest as a single unsigned big-endian
   integer, and reduce it modulo 100. Written out in Python that is exactly:

   ```python
   bucket = int(hashlib.sha256(f"{flag_key}:{user_id}".encode("utf-8")).hexdigest(), 16) % 100
   ```

4. The user is enabled when `bucket < percentage`.

Do **not** use the builtin `hash()`, `id()`, `zlib.crc32` seeded by anything
process-local, or any other digest. A cryptographic digest is required here, and
it is required to be SHA-256 specifically, because the Go and TypeScript SDKs
implement the same four lines and their answers must match ours character for
character.

Worked example: `flag_key="checkout-v2"`, `user_id="user-1042"`. The material is
`"checkout-v2:user-1042"`, whose SHA-256 reduces to bucket **19**. So
`is_enabled("checkout-v2", "user-1042", 19)` is `False` (19 is not `< 19`) and
`is_enabled("checkout-v2", "user-1042", 20)` is `True`. The same user under
`flag_key="search-rerank"` lands in bucket 10 and is therefore already enabled
at 11%.

## Monotonicity

This is the requirement that broke us, so it is called out on its own. For a
fixed `flag_key` and `user_id`:

> if `is_enabled(flag_key, user_id, p)` is `True`, then
> `is_enabled(flag_key, user_id, q)` must also be `True` for every `q > p`.

Ramping a flag up may only ever *add* users to the enabled set. It may never
remove one. This falls out of the rule above for free — the bucket does not
depend on `percentage`, so widening the threshold only admits more buckets — but
it is easy to destroy by folding the percentage, the ramp step number, or a
per-step salt into the hash material. Don't.

## Percentage boundaries

`percentage` counts buckets, and buckets run `0`–`99`:

- `percentage = 0` disables **everyone**: no bucket is `< 0`.
- `percentage = 100` enables **everyone**: every bucket `0`–`99` is `< 100`.
  There is no user anywhere who is still off at 100%.

## Errors

Validate the argument **types first**, then the range:

- `flag_key` or `user_id` that is not a `str` raises `TypeError`.
- `percentage` that is not an `int` raises `TypeError`. This includes `float`,
  even an integral one like `50.0`, and it includes `bool` — `True` and `False`
  are instances of `int` in Python but they are not percentages, so they raise
  `TypeError` too.
- `percentage` that is an `int` outside the inclusive range `0`–`100` raises
  `ValueError`.

Because types are checked before the range, `is_enabled("f", "u", 101.0)` raises
`TypeError`, not `ValueError`.

An empty `flag_key` or an empty `user_id` is **not** an error. Empty strings are
legitimate — the analytics job evaluates flags for anonymous sessions with an
empty user id — and they hash like any other string. `is_enabled("", "", 36)` is
`True`, because `":"` hashes to bucket 35.

Non-ASCII identifiers are also legitimate and are covered by the UTF-8 encoding
step; nothing else about them is special.

## Out of scope

- Attribute-based targeting, allow-lists, and per-environment overrides. Those
  are resolved by the caller before we ever get here.
- Sticky overrides for QA accounts.
- Any I/O, caching, or logging. The function is pure and takes no clock, no
  random source, and no configuration.
