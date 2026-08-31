"""Independent oracle for RATE-338 (token_bucket).

Deliberately structured differently from the obvious single-pass, float-state
loop:

  * arithmetic is done in EXACT RATIONALS (``fractions.Fraction``) rather than
    binary floating point, so no accrual drift can accumulate at all; and
  * the bucket state is not carried in a running variable.  Instead, for every
    index ``i`` the whole prefix ``requests[:i+1]`` is REPLAYED from scratch
    (O(n^2) brute force) to recompute the token count and the accrual mark.
    That makes it structurally impossible to "leak" a state update out of, or
    into, the wrong branch the way the INC-2251 bug does.

Standard library only, deterministic, no network.
"""

from __future__ import annotations

import math
from fractions import Fraction

ORACLE_NOTES = """
Based on RFC 2697 (A Single Rate Three Color Marker), plus the one deliberate
deviation the ticket declares (continuous accrual instead of the RFC's discrete
CIR-times-per-second ticks).

Clauses checked, verbatim from the RFC:
  * "The token buckets C and E are initially (at time 0) full, i.e., the token
    count Tc(0) = CBS and the token count Te(0) = EBS."   -> bucket starts full
    at ``capacity``; the accrual mark starts at the first entry's timestamp.
  * "If Tc is less than CBS, Tc is incremented by one, else ..."   -> the token
    count is never incremented past CBS, i.e. the clamp
    ``tokens = min(capacity, ...)`` in step 1.
  * "If Tc(t)-B >= 0, the packet is green and Tc is decremented by B down to
    the minimum value of 0"   -> admission is the INCLUSIVE comparison (a cost
    exactly equal to the credit on hand is admitted), and the decrement is
    floored at 0.  The ticket's ``tokens + 1e-9 >= cost`` is that same
    inclusive test with an absolute slack bolted on.
  * The RFC has no third branch for our single bucket: a packet that is not
    green (here: rejected) decrements nothing.  Tc is left exactly as the
    increment step left it -> "a rejection consumes nothing".
  * RFC 2697 has no notion of the accrual clock being contingent on the
    marking outcome: token increments happen on the clock, unconditionally.
    That is the INC-2251 rule (advance the accrual mark on EVERY entry).

Implementation independence: exact Fraction arithmetic + O(n^2) prefix replay,
so the reference's float accumulation and its single-pass state machine are
both cross-checked rather than mirrored.  Accrual is exact; only the admission
comparison of step 3 is evaluated in doubles, because the ticket writes that
step as a literal float expression (see point 5 below).

Things I found questionable in SPEC.md:

  1. CITATION IS OFF BY ONE SECTION.  SPEC.md and task.yaml both cite
     "RFC 2697, section 2" for the meter.  Section 2 of RFC 2697 is
     "Configuration" (it only defines CIR / CBS / EBS and the "at least one of
     CBS/EBS larger than 0" constraint).  The clauses the ticket actually
     relies on -- Tc(0) = CBS, the increment rule with its CBS clamp, and the
     "Tc(t)-B >= 0 ... decremented by B down to the minimum value of 0" test --
     are all in section 3, "Metering".  Cosmetic, but a reimplementer sent to
     section 2 will not find the semantics described there.

  2. STEP 4's ``max(0.0, tokens - cost)`` IS OBSERVABLE, and the spec does not
     say so.  Because admission uses a 1e-9 slack, a request can be admitted
     while ``cost`` exceeds ``tokens`` by up to 1e-9; the clamp then silently
     donates up to 1e-9 tokens back to the bucket instead of going negative.
     This matches the RFC ("decremented by B down to the minimum value of 0"),
     so I implemented it as written, but the spec presents the clamp as if it
     were a no-op safety net.

  3. TYPE ERRORS ARE UNDER-DETERMINED.  The spec says to raise ValueError when
     an argument "is not a finite number", which literally covers
     ``capacity="10"``; a natural implementation would raise TypeError there
     instead.  The generators never produce non-numeric input, so this is
     untested either way.  I coerce and raise ValueError; I do NOT treat a
     reference that raises TypeError as a defect.

  4. The two open questions in task.yaml (negative epochs are fine, ValueError
     wording unconstrained) I agree are genuine under-determination, not
     defects.  My oracle accepts any finite epoch, including negative.

  5. THE SLACK HAS ITS OWN KNIFE EDGE, which the spec does not acknowledge.
     Step 3's stated purpose is to make the boundary "well defined in the face
     of floating point drift", but the rule is itself a float expression, so
     the boundary merely MOVES to cost == tokens + 1e-9 and is decided there by
     binary rounding.  Concretely, simulate(1.0, 1.0, [(0.0, 1.000000001)]):
     the exact rational sum 1 + 1e-9 is strictly less than the double
     1.000000001, so exact arithmetic rejects, while the double sum
     1.0 + 1e-9 rounds to exactly 1.000000001 and admits.  The reference
     admits.  I agree with the reference -- the spec's formula is literal and
     `tokens + 1e-9 >= cost` in doubles is what it says -- but any
     reimplementation using Decimal, Fraction, or a different association order
     will differ at that one input.  Under-determination, not a defect; worth a
     sentence in SPEC.md if the corpus wants bit-exact reimplementations.
     Everywhere else exact-vs-float divergence is ~1e-16, seven orders of
     magnitude below the slack, and cannot flip a decision -- verified on
     traces of 50,000 entries with 10 ms gaps.
""".strip()


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

def _finite(value, what: str) -> Fraction:
    """Coerce to an exact rational, raising ValueError unless finite."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):  # bool is an int; arithmetic treats it as 0/1
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{what} must be finite, got {value!r}")
        return Fraction(value)
    # Anything else: the spec only ever promises ValueError.
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{what} must be a finite number, got {value!r}")
    if not math.isfinite(as_float):
        raise ValueError(f"{what} must be finite, got {value!r}")
    return Fraction(as_float)


def _validate(capacity, refill_per_second, requests):
    """Return (capacity, rate, [(t, cost)]) as exact rationals, or raise."""
    cap = _finite(capacity, "capacity")
    if cap <= 0:
        raise ValueError("capacity must be greater than zero")

    rate = _finite(refill_per_second, "refill_per_second")
    if rate <= 0:
        raise ValueError("refill_per_second must be greater than zero")

    trace: list[tuple[Fraction, Fraction]] = []
    previous: Fraction | None = None
    for index, entry in enumerate(requests):
        timestamp, cost = entry
        stamp = _finite(timestamp, f"timestamp[{index}]")
        price = _finite(cost, f"cost[{index}]")
        if price < 0:
            raise ValueError(f"cost[{index}] must not be negative")
        if previous is not None and stamp < previous:
            raise ValueError(f"timestamp[{index}] regresses: corrupt trace")
        previous = stamp
        trace.append((stamp, price))

    return cap, rate, trace


# ---------------------------------------------------------------------------
# the oracle: brute-force prefix replay in exact rational arithmetic
# ---------------------------------------------------------------------------

# The ticket's absolute admission slack, as the exact value of the float 1e-9.
_SLACK = Fraction(1e-9)


def _admits(tokens: Fraction, cost: Fraction) -> bool:
    """SPEC step 3: ``tokens + 1e-9 >= cost``.

    Evaluated the way the ticket writes it -- in IEEE doubles -- rather than in
    exact rationals.  This matters only on the knife edge where ``cost`` sits
    within one ulp of ``tokens + 1e-9`` (e.g. capacity=1.0, cost=1.000000001):
    there the exact sum and the rounded float sum straddle ``cost``, and the
    ticket's literal formula is what decides.  Everywhere else the two readings
    agree, since exact-vs-float accrual drift here is ~1e-16, seven orders of
    magnitude below the slack.
    """
    return float(tokens) + 1e-9 >= float(cost)


def _replay(capacity: Fraction, rate: Fraction,
            trace: list[tuple[Fraction, Fraction]], upto: int) -> bool:
    """Replay trace[0 .. upto] from a full bucket; return the decision at `upto`.

    Everything is recomputed from the initial condition every time -- no state
    survives between calls -- which is the point: the accrual mark cannot be
    accidentally carried across a branch.
    """
    tokens = capacity                 # RFC 3: Tc(0) = CBS, the bucket is full
    mark = trace[0][0]                # accrual mark starts at the first stamp
    decision = False

    for stamp, cost in trace[:upto + 1]:
        # 1. bring the bucket up to date, never above CBS
        accrued = (stamp - mark) * rate
        tokens = tokens + accrued
        if tokens > capacity:
            tokens = capacity
        # 2. the clock is not contingent on the outcome (INC-2251)
        mark = stamp
        # 3. inclusive comparison with absolute slack
        decision = _admits(tokens, cost)
        # 4. only an admitted request spends anything; floor at 0
        if decision:
            tokens = tokens - cost
            if tokens < 0:
                tokens = Fraction(0)

    return decision


# Above this length the O(n^2) replay stops being merely slow.  The generators
# never produce traces longer than 12, so every fuzzed input takes the
# brute-force path; the linear fallback exists only so that hand-written
# stress traces (tens of thousands of entries) terminate.  Both paths use the
# same exact-rational arithmetic.
_BRUTE_FORCE_LIMIT = 400


def _stream(capacity: Fraction, rate: Fraction,
            trace: list[tuple[Fraction, Fraction]]) -> list[bool]:
    """Linear exact-arithmetic pass, used only for very long traces."""
    tokens = capacity
    mark = trace[0][0]
    out: list[bool] = []
    for stamp, cost in trace:
        tokens = min(capacity, tokens + (stamp - mark) * rate)
        mark = stamp
        admitted = _admits(tokens, cost)
        if admitted:
            tokens = max(Fraction(0), tokens - cost)
        out.append(admitted)
    return out


def oracle(capacity, refill_per_second, requests):
    cap, rate, trace = _validate(capacity, refill_per_second, requests)
    if not trace:
        return []
    if len(trace) > _BRUTE_FORCE_LIMIT:
        return _stream(cap, rate, trace)
    return [_replay(cap, rate, trace, i) for i in range(len(trace))]


# Alias so the file can also be exercised under the task's entrypoint name.
simulate = oracle


# ---------------------------------------------------------------------------
# values derived from the ticket's worked example and from RFC 2697 section 3
# ---------------------------------------------------------------------------

KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # SPEC.md "Worked example" table, verbatim.  Entry 2 accrues from t=5, not
    # t=0, because the accrual mark advanced across the rejection (INC-2251).
    ((10.0, 1.0, [(0.0, 10.0), (5.0, 10.0), (6.0, 10.0), (10.0, 10.0)]), {},
     [True, False, False, True]),

    # RFC 2697 s.3: "the token buckets C and E are initially (at time 0) full".
    # The very first request may therefore spend the entire bucket.
    ((5.0, 1.0, [(0.0, 5.0)]), {}, [True]),

    # An empty trace returns an empty list (SPEC.md, Errors).
    ((1.0, 1.0, []), {}, []),

    # INC-2214: continuous accrual.  100 ms polls at 1 token/s accrue 0.1 each,
    # exactly the cost, so every poll is admitted.  floor() would starve this.
    ((1.0, 1.0, [(0.0, 1.0), (0.1, 0.1), (0.2, 0.1), (0.3, 0.1), (0.4, 0.1),
                 (0.5, 0.1)]), {},
     [True, True, True, True, True, True]),

    # Sub-second gap at a fractional rate: 0.1 s * 3/s = 0.3 tokens exactly,
    # admitted; the repeated timestamp accrues nothing, so it is rejected.
    ((1.0, 3.0, [(0.0, 1.0), (0.1, 0.3), (0.1, 0.3)]), {},
     [True, True, False]),

    # RFC 2697 s.3: "If Tc is less than CBS, Tc is incremented by one" -- the
    # count is never raised past CBS.  1000 tokens of idle credit clamp to 5.
    ((5.0, 10.0, [(0.0, 5.0), (100.0, 5.0), (100.0, 1.0)]), {},
     [True, True, False]),

    # RFC 2697 s.3: "If Tc(t)-B >= 0, the packet is green" -- inclusive.  A cost
    # exactly equal to the credit on hand is admitted.
    ((2.0, 1.0, [(0.0, 2.0), (1.0, 1.0), (1.5, 0.5)]), {},
     [True, True, True]),

    # ... and a hair over the credit on hand is not.
    ((2.0, 1.0, [(0.0, 2.0), (1.0, 1.5)]), {}, [True, False]),

    # A non-green packet decrements nothing (the RFC only decrements Tc on the
    # green branch): the oversized request leaves the full bucket behind.
    ((5.0, 1.0, [(0.0, 6.0), (0.0, 5.0)]), {}, [False, True]),

    # Same rule at ordinary sizes: the rejected 2-token request does not drain
    # the 1 token that the following request needs.
    ((5.0, 1.0, [(0.0, 4.0), (0.0, 2.0), (0.0, 1.0)]), {}, [True, False, True]),

    # A burst sharing one timestamp accrues nothing between its members.
    ((3.0, 1.0, [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]), {},
     [True, True, True, False]),

    # A zero cost is always admitted, even against an empty bucket (0 - 0 >= 0).
    ((1.0, 1.0, [(0.0, 1.0), (0.0, 0.0)]), {}, [True, True]),

    # Timestamps may sit on any finite epoch, including a negative one; only
    # differences are used.  -3.0 -> -2.5 accrues 0.5 * 2 = 1.0 token.
    ((2.0, 2.0, [(-3.0, 2.0), (-2.5, 1.0), (-2.5, 1.0)]), {},
     [True, True, False]),

    # A cost above CBS can never be met however long the customer waits.
    ((1.0, 5.0, [(0.0, 2.0), (60.0, 2.0)]), {}, [False, False]),

    # --- error contract ---
    ((1.0, 1.0, [(1.0, 0.5), (0.5, 0.5)]), {}, ("raises", "ValueError")),
    ((1.0, 1.0, [(0.0, -0.25)]), {}, ("raises", "ValueError")),
    ((0.0, 1.0, [(0.0, 0.0)]), {}, ("raises", "ValueError")),
    ((1.0, -2.0, [(0.0, 0.5)]), {}, ("raises", "ValueError")),
    ((float("inf"), 1.0, [(0.0, 0.5)]), {}, ("raises", "ValueError")),
    ((1.0, float("nan"), [(0.0, 0.5)]), {}, ("raises", "ValueError")),
    ((1.0, 1.0, [(float("nan"), 0.5)]), {}, ("raises", "ValueError")),
    ((1.0, 1.0, [(0.0, float("inf"))]), {}, ("raises", "ValueError")),
]
