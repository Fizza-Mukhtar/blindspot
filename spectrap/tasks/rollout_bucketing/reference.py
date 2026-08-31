"""Reference implementation for FLAG-238 (consistent percentage rollout).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority:
  - Monotonic gradual rollout, "Hashing it right: solving a gradual rollout
    puzzle" --
    https://www.getunleash.io/blog/hashing-it-right-solving-a-gradual-rollout-puzzle
  - Why the builtin ``hash()`` is disqualified: it is salted per process unless
    PYTHONHASHSEED is pinned --
    https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED
"""

from __future__ import annotations

import hashlib

# Buckets are numbered 0..99, so `percentage` is literally a bucket count and
# `percentage == 100` admits every bucket that exists.
_BUCKET_COUNT = 100

_MIN_PERCENTAGE = 0
_MAX_PERCENTAGE = 100


def _bucket(flag_key: str, user_id: str) -> int:
    """Assign the pair to a bucket in 0..99.

    The hash material is pinned by the ticket as ``f"{flag_key}:{user_id}"``
    encoded UTF-8, digested with SHA-256, read as one big unsigned integer and
    reduced modulo 100.  A cryptographic digest is mandatory: the builtin
    ``hash()`` is randomised per process, which is what made the same user flap
    between workers.

    Note that `percentage` is deliberately absent from the material.  That
    absence *is* the monotonicity guarantee: the bucket is a property of the
    pair alone, so raising the threshold can only ever admit more users.
    """
    material = f"{flag_key}:{user_id}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    return int(digest, 16) % _BUCKET_COUNT


def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    """Return whether this user is inside the rollout for this flag."""
    # Types first, then range -- the ticket fixes this order so that a float
    # like 101.0 is a TypeError rather than a ValueError.
    if not isinstance(flag_key, str):
        raise TypeError(f"flag_key must be a str, got {type(flag_key).__name__}")
    if not isinstance(user_id, str):
        raise TypeError(f"user_id must be a str, got {type(user_id).__name__}")
    # bool subclasses int, but True/False are not percentages.
    if isinstance(percentage, bool) or not isinstance(percentage, int):
        raise TypeError(f"percentage must be an int, got {type(percentage).__name__}")
    if not (_MIN_PERCENTAGE <= percentage <= _MAX_PERCENTAGE):
        raise ValueError(f"percentage must be between 0 and 100, got {percentage}")

    # Empty flag_key / user_id are legitimate and hash like any other string.
    # percentage == 0 -> no bucket is < 0 -> everyone off.
    # percentage == 100 -> every bucket 0..99 is < 100 -> everyone on.
    return _bucket(flag_key, user_id) < percentage
