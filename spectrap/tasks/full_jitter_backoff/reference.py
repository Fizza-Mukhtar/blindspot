"""Reference implementation for PLAT-2291 (Full Jitter retry schedule).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: AWS Architecture Blog, "Exponential Backoff And Jitter"
https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
The Full Jitter variant given there is

    sleep = random_between(0, min(cap, base * 2 ** attempt))

with ``attempt`` starting at 0.  The cap bounds the *ceiling of the draw*, and
there is no additive term; ``base + random_between(...)`` is the post's Equal
Jitter variant, a different algorithm.
"""

from __future__ import annotations

import math
from typing import Callable

RandFn = Callable[[float], float]


def _positive_finite(name: str, value: float) -> float:
    """Reject the values that cannot describe a delay bound.

    ``nan`` is checked through ``math.isfinite`` rather than a comparison
    because every ordering comparison against ``nan`` is False, so a plain
    ``value <= 0`` guard would let it through and poison the whole schedule.
    """
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be a finite number greater than zero, got {value!r}")
    return number


def schedule(attempts: int, base: float, cap: float, rand: RandFn) -> list[float]:
    """Return the Full Jitter delays for ``attempts`` retries, attempt 0 first."""
    # Validation order is fixed by the ticket: attempts, then base, then cap.
    if attempts < 0:
        raise ValueError(f"attempts must not be negative, got {attempts!r}")
    base_seconds = _positive_finite("base", base)
    cap_seconds = _positive_finite("cap", cap)

    # ceiling_0 = min(cap, base * 2**0) = min(cap, base).  cap < base is legal
    # and simply flattens the whole schedule to cap.
    ceiling = base_seconds if base_seconds < cap_seconds else cap_seconds

    delays: list[float] = []
    for _ in range(attempts):
        # Exactly one draw per attempt, from [0, ceiling_i].  The value is
        # returned as drawn: no clamping after the fact, no additive base.
        delays.append(float(rand(ceiling)))

        # Advance to ceiling_{i+1} = min(cap, base * 2**(i+1)) by doubling.
        # Doubling is exact in binary floating point, and stopping once the
        # ceiling has reached cap keeps the value finite no matter how large
        # `attempts` is -- evaluating 2**i directly would blow up instead.
        if ceiling < cap_seconds:
            doubled = ceiling * 2.0
            ceiling = doubled if doubled < cap_seconds else cap_seconds

    return delays
