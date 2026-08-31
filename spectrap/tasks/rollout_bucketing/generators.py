"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the reference
on each input, and keeps the first input where they disagree.  Uniform random
inputs would be nearly useless here: a wrong implementation and a right one
agree on the overwhelming majority of ``(pair, percentage)`` triples, and only
diverge in three narrow places.  So the space is biased towards them:

  * the **threshold boundary** -- the percentage at which a given pair flips on.
    ``<`` versus ``<=`` and 0-based versus 1-based buckets are invisible
    everywhere else, so this generator re-derives the reference bucket for the
    chosen pair and aims percentages at ``bucket - 1``, ``bucket``,
    ``bucket + 1`` a large fraction of the time.
  * the **percentage extremes** 0, 1, 99 and 100, where "disable everyone" and
    "enable everyone" are asserted.
  * the **hash material corners** -- empty identifiers, identifiers containing
    the ``:`` separator itself, and non-ASCII identifiers that only agree once
    the input is UTF-8 encoded.

A minority of samples (~20%) are deliberately invalid, split between the
TypeError cases (wrong argument types, including ``bool`` and integral floats)
and the ValueError cases (in-type percentages outside 0..100).
"""

from __future__ import annotations

import hashlib
import random

FLAG_KEYS = [
    "checkout-v2",
    "search-rerank",
    "new-nav",
    "billing-retry",
    "",  # empty flag key is legitimate
    "a",
    "a:b",  # contains the separator
    "flag:with:colons",
    "ünïcode-flag",
    "F",
    "f",
    "checkout_v2",
]

USER_IDS = [
    "user-0",
    "user-1",
    "user-7",
    "user-42",
    "user-1042",
    "ana@example.com",
    "",  # anonymous session
    "b:c",  # contains the separator
    "üser-é☃",
    "0",
    "00",
    "USER-42",
    "0123456789abcdef" * 4,
]

BAD_PERCENT_TYPES = [50.0, 0.0, 100.0, 101.0, "50", "0", None, True, False, (50,)]
OUT_OF_RANGE = [-1, 101, -100, 1000, -(10**9), 10**9]
BAD_IDENTIFIERS = [None, 42, b"user-42", ["user-42"], 3.5]


def _bucket(flag_key: str, user_id: str) -> int:
    """The reference bucket, re-derived only so we can aim at its boundary."""
    material = f"{flag_key}:{user_id}".encode("utf-8")
    return int(hashlib.sha256(material).hexdigest(), 16) % 100


def sample(rng: random.Random) -> tuple[tuple, dict]:
    roll = rng.random()

    if roll < 0.08:
        # TypeError: percentage of the wrong type.
        return (
            rng.choice(FLAG_KEYS),
            rng.choice(USER_IDS),
            rng.choice(BAD_PERCENT_TYPES),
        ), {}

    if roll < 0.16:
        # ValueError: an int percentage outside the inclusive 0..100 range.
        return (
            rng.choice(FLAG_KEYS),
            rng.choice(USER_IDS),
            rng.choice(OUT_OF_RANGE),
        ), {}

    if roll < 0.20:
        # TypeError: a non-str identifier.
        flag_key: object = rng.choice(FLAG_KEYS)
        user_id: object = rng.choice(USER_IDS)
        if rng.random() < 0.5:
            flag_key = rng.choice(BAD_IDENTIFIERS)
        else:
            user_id = rng.choice(BAD_IDENTIFIERS)
        return (flag_key, user_id, rng.randint(0, 100)), {}

    key = rng.choice(FLAG_KEYS)
    uid = rng.choice(USER_IDS)

    shape = rng.random()
    if shape < 0.45:
        # Straddle the exact flip-on threshold for this pair.
        bucket = _bucket(key, uid)
        percentage = min(100, max(0, bucket + rng.choice((-1, 0, 1))))
    elif shape < 0.70:
        percentage = rng.choice((0, 0, 1, 99, 100, 100))
    else:
        percentage = rng.randint(0, 100)

    return (key, uid, percentage), {}


# Tried first, before random sampling.  These encode every corner the ticket
# names: the worked example and its off-by-one neighbour, the 0/100 extremes,
# empty identifiers, the ``:`` collision pair, UTF-8, and each error class.
SEEDS: list[tuple[tuple, dict]] = [
    (("checkout-v2", "user-1042", 19), {}),  # worked example: bucket 19, off
    (("checkout-v2", "user-1042", 20), {}),  # ... on at 20
    (("search-rerank", "user-1042", 11), {}),  # same user, other flag: bucket 10
    (("checkout-v2", "user-7", 96), {}),  # high bucket still off at 96
    (("checkout-v2", "user-7", 97), {}),  # ... on at 97
    (("new-nav", "user-0", 0), {}),  # percentage 0 disables everyone
    (("new-nav", "user-0", 100), {}),  # percentage 100 enables everyone
    (("", "", 35), {}),  # empty identifiers hash normally: bucket 35
    (("", "", 36), {}),  # ... on at 36
    (("a:b", "c", 7), {}),  # separator collision, half one
    (("a", "b:c", 7), {}),  # ... half two: same material "a:b:c"
    (("billing-retry", "üser-é☃", 55), {}),  # UTF-8 material, bucket 54
    (("f", "u", 101), {}),  # invalid: above the range
    (("f", "u", -1), {}),  # invalid: below the range
    (("f", "u", 50.0), {}),  # invalid: integral float is not an int
    (("f", "u", True), {}),  # invalid: bool is not a percentage
]
