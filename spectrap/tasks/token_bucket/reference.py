"""Reference implementation for RATE-338 (offline token-bucket replay).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: RFC 2697 section 2 (the committed bucket of the single rate three
color marker) -- https://datatracker.ietf.org/doc/html/rfc2697 -- for the
credit-accumulation semantics: the bucket starts full, the token count is never
incremented past CBS, a request is green when the count covers its size, and a
non-green request leaves the count untouched.  The RFC adds credit in discrete
ticks; RATE-338 accrues continuously instead, which is the only deliberate
deviation.
"""

from __future__ import annotations

import math

# Absolute slack on the admission comparison, fixed by the ticket so that a
# request costing exactly the credit on hand is admitted rather than falling
# foul of floating point drift.
_EPSILON = 1e-9


def _require_positive(name: str, value: float) -> float:
    """capacity and refill_per_second must be finite and strictly positive."""
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be a finite positive number, got {value!r}")
    return number


def simulate(
    capacity: float,
    refill_per_second: float,
    requests: list[tuple[float, float]],
) -> list[bool]:
    """Replay a request trace against a token bucket, one decision per entry."""
    size = _require_positive("capacity", capacity)
    rate = _require_positive("refill_per_second", refill_per_second)

    # RFC 2697 s2: "the token count Tc is initially (at time 0) full, i.e.,
    # Tc(0) = CBS."
    tokens = size
    accrual_mark: float | None = None
    decisions: list[bool] = []

    for index, entry in enumerate(requests):
        timestamp, cost = entry
        timestamp = float(timestamp)
        cost = float(cost)

        if not math.isfinite(timestamp):
            raise ValueError(f"request {index}: timestamp must be finite, got {timestamp!r}")
        if not math.isfinite(cost) or cost < 0.0:
            raise ValueError(f"request {index}: cost must be finite and non-negative, got {cost!r}")

        if accrual_mark is None:
            # The bucket starts full at the first entry, so accrual before it
            # would be clamped away regardless of where the mark is placed.
            accrual_mark = timestamp
        elif timestamp < accrual_mark:
            raise ValueError(
                f"request {index}: timestamps must be non-decreasing, "
                f"{timestamp!r} follows {accrual_mark!r}"
            )

        # Continuous, fractional accrual -- no flooring, no whole-second
        # bucketing (INC-2214) -- clamped at the bucket size, which is the RFC's
        # "if Tc < CBS, Tc is incremented" rule.
        tokens = min(size, tokens + (timestamp - accrual_mark) * rate)

        # The mark advances for every entry, admitted or rejected (INC-2251).
        accrual_mark = timestamp

        # RFC 2697 s2: green when Tc - B >= 0, decrement by B; otherwise Tc is
        # unchanged.  The epsilon makes the equality boundary well defined.
        admitted = tokens + _EPSILON >= cost
        if admitted:
            tokens = max(0.0, tokens - cost)
        decisions.append(admitted)

    return decisions
