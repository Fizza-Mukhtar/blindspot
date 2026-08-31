"""Independent oracle for PLAT-2291 (full_jitter_backoff).

Derived from the AWS Architecture Blog post "Exponential Backoff And Jitter"
(https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) and
from SPEC.md.  reference.py and selftest.py were NOT read.
"""

from __future__ import annotations

import math
from fractions import Fraction

ORACLE_NOTES = """
Based on the AWS Architecture Blog post "Exponential Backoff And Jitter", which
states the four variants as one-line formulas:

    No Jitter          sleep = min(cap, base * 2 ** attempt)
    Full Jitter        sleep = random(0, min(cap, base * 2 ** attempt))
    Equal Jitter       sleep = min(cap, base * 2 ** attempt) / 2
                               + random(0, min(cap, base * 2 ** attempt) / 2)
    Decorrelated       sleep = min(cap, random(base, sleep * 3))

Only the Full Jitter clause governs this ticket.  The three things it decides,
and which SPEC.md restates correctly:
  * the min(cap, .) is INSIDE random(0, .), so cap bounds the ceiling of the
    draw, not the drawn value (contrast: min(cap, random(0, base*2**attempt)));
  * there is no additive term -- the additive `X/2 +` form is the Equal Jitter
    line, a different algorithm;
  * `attempt` is the attempt index and the formula is applied for every attempt
    including the first, so with 0-based indexing element 0 is
    random(0, min(cap, base)) and never a flat `base`.

DIFFERENT ALGORITHM / STRUCTURE (deliberate, so a shared mistake cannot hide):
the reference presumably iterates a float ceiling and clamps the exponent.  This
oracle instead builds the ceiling table with EXACT rational arithmetic:
Fraction(base) * (1 << i) is computed exactly (arbitrary precision, so it can
never overflow or round), compared exactly against Fraction(cap), and only
converted to float once it is known to be below cap.  The saturation point is
therefore discovered by exact comparison rather than by clamping the exponent,
and no float ever holds an intermediate 2**i.  Multiplication by a power of two
is exact in binary floating point, so float(Fraction(base) * 2**i) is bit-identical
to the ideally-rounded base * 2**i wherever the latter is representable; where it
is not representable the exact comparison has already selected `cap`.

Clauses/conditions checked: the Full Jitter formula itself; attempt numbering
from 0; cap applied before the draw; exactly one rand call per attempt in
attempt order with the ceiling as sole argument; the returned draw passed
through unmodified; cap < base and cap == base giving a flat ceiling of cap;
attempts == 0 -> []; attempts < 0 -> ValueError; base/cap finite and > 0 (nan
must be rejected explicitly since nan <= 0 is False); validation order
attempts, base, cap with the parameter name in the message.

AMBIGUITY / POSSIBLE SPEC PROBLEMS (reported, not treated as defects):
  1. SPEC.md says "Every returned delay must be a finite number in [0, cap]"
     while also saying "Return each drawn value unchanged: do not clamp it".
     These two sentences conflict for a `rand` that violates its own [0, upper]
     contract.  The tie-breaker is "Treat it as trustworthy" plus the explicit
     out-of-scope item "Validating ... that it honours its contract", so the
     [0, cap] sentence is read as a consequence of a well-behaved rand, not as a
     post-condition to enforce.  This oracle does NOT clamp.  A reference that
     clamps would diverge only for a contract-violating rand, which the
     generator never produces.
  2. Whether the returned elements are coerced to float or handed back with
     whatever type rand returned is left open (task.yaml agrees).  This oracle
     returns rand's value unchanged, un-coerced; the reference was observed
     (by calling it, not by reading it) to coerce with float().  Both readings
     satisfy SPEC.md, and the difference is unobservable for any rand that
     returns a float, which is every rand the generator produces.
  3. No upper bound on `attempts` is specified; this oracle imposes none.
  4. The type of `attempts` is unspecified (only `< 0` is defined as an error);
     a float attempts such as 2.5 is under-determined.  Not exercised by the
     generator.
Nothing in SPEC.md contradicts the blog post: SPEC.md's worked example
[0.2, 0.4, 0.8, 1.6, 3.2, 5.0] for base=0.2, cap=5.0, rand=identity is exactly
min(cap, base * 2 ** i) for i = 0..5.
""".strip()


def _ceilings(attempts: int, base: float, cap: float) -> list[float]:
    """Exact-rational ceiling table: ceiling_i = min(cap, base * 2**i).

    ``base * 2**i`` is evaluated in exact rational arithmetic, so the point at
    which the ceiling saturates at ``cap`` is found by an exact comparison
    instead of by clamping the exponent or by float doubling.
    """
    exact_base = Fraction(base)
    exact_cap = Fraction(cap)
    out: list[float] = []
    pow2 = 1  # exact 2**i, arbitrary precision integer
    for _ in range(attempts):
        if pow2 is None:  # already saturated: every later ceiling is cap
            out.append(cap)
            continue
        value = exact_base * pow2
        if value >= exact_cap:
            out.append(cap)
            pow2 = None
        else:
            # value < cap <= max finite float, so this conversion cannot overflow.
            out.append(float(value))
            pow2 <<= 1
    return out


def _require_positive_finite(name: str, value) -> None:
    """`nan` must be rejected explicitly: `nan <= 0` is False."""
    try:
        ok = math.isfinite(value) and value > 0
    except (TypeError, ValueError):
        ok = False
    if not ok:
        raise ValueError("%s must be a finite number > 0, got %r" % (name, value))


def oracle(attempts, base, cap, rand):
    # Validation order is mandated: attempts, then base, then cap.
    if attempts < 0:
        raise ValueError("attempts must be >= 0, got %r" % (attempts,))
    _require_positive_finite("base", base)
    _require_positive_finite("cap", cap)

    # One rand call per attempt, in attempt order, with the ceiling as its only
    # argument; the drawn value is returned unchanged.
    return [rand(ceiling) for ceiling in _ceilings(attempts, base, cap)]


# ---------------------------------------------------------------------------
# Known values.
#
# With rand = lambda u: u the schedule collapses to the blog post's *No Jitter*
# line, min(cap, base * 2 ** attempt), which is what makes these hand-checkable
# straight from the standard.  With rand = lambda u: u / 2 it collapses to the
# first term of the blog's *Equal Jitter* line, min(cap, base*2**attempt)/2 --
# note that this is NOT the Equal Jitter delay, which adds a second random term
# on top; the difference is exactly the trap.
# ---------------------------------------------------------------------------

_MAX = lambda u: u        # noqa: E731  - draw the top of the interval
_ZERO = lambda u: 0.0     # noqa: E731  - draw the bottom of the interval
_HALF = lambda u: u / 2   # noqa: E731
_TENTH = lambda u: u / 10  # noqa: E731

KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # SPEC.md's worked example, verbatim: ceilings 0.2 0.4 0.8 1.6 3.2 5.0.
    ((6, 0.2, 5.0, _MAX), {}, [0.2, 0.4, 0.8, 1.6, 3.2, 5.0]),
    # Same example, rand -> 0: the draw is the whole delay, so all zeros.
    ((6, 0.2, 5.0, _ZERO), {}, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    # Same example halved.  Last element is cap/2 = 2.5, not cap: the cap bounds
    # the ceiling of the draw, not the drawn delay.  A clamp-after-draw
    # implementation returns 3.2 here (min(cap, 6.4/2)).
    ((6, 0.2, 5.0, _HALF), {}, [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]),
    # Attempt 0 is already jittered: element 0 is rand(min(cap, base)), never a
    # flat `base`.  An unjittered-first-hop implementation returns [1.0].
    ((1, 1.0, 10.0, _ZERO), {}, [0.0]),
    ((3, 1.0, 10.0, _ZERO), {}, [0.0, 0.0, 0.0]),
    # No additive term: with rand -> u/10 the delays are ceiling/10 exactly.
    # Equal Jitter would give ceiling/2 + ceiling/20.
    ((4, 1.0, 100.0, _TENTH), {}, [0.1, 0.2, 0.4, 0.8]),
    # Ceiling sequence saturating at cap partway through (i>=4 here).
    ((7, 1.0, 10.0, _MAX), {}, [1.0, 2.0, 4.0, 8.0, 10.0, 10.0, 10.0]),
    # cap < base: every ceiling is cap, including attempt 0's.
    ((5, 10.0, 2.0, _MAX), {}, [2.0, 2.0, 2.0, 2.0, 2.0]),
    # cap == base: same flat behaviour.
    ((4, 3.0, 3.0, _MAX), {}, [3.0, 3.0, 3.0, 3.0]),
    # cap == base * 2**i exactly at i=2: min() takes cap, same value either way.
    ((4, 0.5, 2.0, _MAX), {}, [0.5, 1.0, 2.0, 2.0]),
    # attempts == 0 is not an error.
    ((0, 1.0, 10.0, _MAX), {}, []),
    # Large attempt counts must not overflow a literal 2 ** attempt.
    ((2000, 1.0, 30.0, _MAX), {}, [1.0, 2.0, 4.0, 8.0, 16.0] + [30.0] * 1995),
    ((1100, 1.0, 30.0, _ZERO), {}, [0.0] * 1100),
    # Errors.
    ((-1, 1.0, 10.0, _MAX), {}, ("raises", "ValueError")),
    ((-4, 1.0, 10.0, _MAX), {}, ("raises", "ValueError")),
    ((3, 0.0, 10.0, _MAX), {}, ("raises", "ValueError")),
    ((3, -1.0, 10.0, _MAX), {}, ("raises", "ValueError")),
    ((3, float("nan"), 10.0, _MAX), {}, ("raises", "ValueError")),
    ((3, float("inf"), 10.0, _MAX), {}, ("raises", "ValueError")),
    ((3, 1.0, 0.0, _MAX), {}, ("raises", "ValueError")),
    ((3, 1.0, -2.0, _MAX), {}, ("raises", "ValueError")),
    ((3, 1.0, float("inf"), _MAX), {}, ("raises", "ValueError")),
    ((3, 1.0, float("nan"), _MAX), {}, ("raises", "ValueError")),
]
