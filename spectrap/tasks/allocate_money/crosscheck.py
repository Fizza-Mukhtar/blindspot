"""Independent oracle for LEDGER-238 (`allocate`).

Written from SPEC.md plus the cited standard (Martin Fowler's Money pattern
`allocate` operation / the largest-remainder a.k.a. Hamilton apportionment
method).  Deliberately structured differently from the obvious
``divmod`` + ``sorted(key=lambda i: (-rem[i], i))`` implementation.
"""

from __future__ import annotations

import math
from fractions import Fraction
from itertools import combinations

ORACLE_NOTES = """
Basis
-----
* SPEC.md (LEDGER-238) as the operative ticket.
* Largest-remainder / Hamilton apportionment as described by the standard
  (https://en.wikipedia.org/wiki/Largest_remainder_method): exact quota,
  integer part first, surplus units to the largest fractional remainders.
  Its worked table (11 seats over votes 47000/16000/15800/12000/6100/3100 ->
  5/2/2/1/1/0) is reproduced verbatim in KNOWN_VALUES.
* Martin Fowler, Money pattern (PoEAA ch. 18), cited by task.yaml for the
  `allocate` operation and the "5 cents two ways is 3 and 2" example.

Algorithm (deliberately NOT the reference shape)
------------------------------------------------
1. Validate first, before any arithmetic (SPEC "Errors": empty weights, any
   negative weight, all-zero weights -> ValueError, regardless of total).
2. Factor the sign out immediately: allocate |total| and negate elementwise
   (SPEC "Negative totals").  Nothing signed is ever floor-divided.
3. Exact claims are computed as `fractions.Fraction(magnitude * w, W)` and the
   integer part with `math.floor` -- exact rational arithmetic, no divmod, no
   binary float anywhere.
4. The leftover units are assigned by BRUTE FORCE, not by sorting: among all
   C(n, leftover) index sets drawn from the payees with a non-zero remainder,
   pick the one maximising the summed remainder; ties are broken by the
   lexicographically smallest sorted index tuple, which is exactly SPEC step 5
   ("largest remainder first, ties to the lowest index").  A greedy
   linear-scan-for-strict-max fallback (also not a sort) covers the rare case
   where the combination count would explode.

Clauses checked
---------------
* conservation: sum(result) == total_cents for every accepted input;
* step 1-2: exact rational quota, floor, remainder = frac part;
* step 4: surplus one unit each, biggest remainder first;
* step 5: tie -> lowest index (the defining clause);
* zero-weight payee receives exactly 0 and can never be reached by step 4;
* negative: allocate(-t, w) == [-x for x in allocate(t, w)], so
  allocate(-5, [1, 1]) == [-3, -2];
* validation precedes allocation, including for total_cents == 0.

Ambiguities / possible spec-vs-standard mismatches
--------------------------------------------------
1. GROUNDING MISMATCH (documentation, not behaviour): Fowler's actual
   `allocate(long[] ratios)` in PoEAA ch. 18 hands the remainder units to the
   FIRST payees in index order (`for i in 0..remainder: results[i]++`), not to
   the largest fractional remainders.  Those two rules coincide on
   allocate(5, [1, 1]) -> [3, 2] (the example the ticket quotes) but diverge
   as soon as the weights are unequal: Fowler would give
   allocate(10, [1, 2, 4]) -> [2, 3, 5], whereas the SPEC's worked example
   says [1, 3, 6].  SPEC.md is internally unambiguous and also names Hamilton,
   so the largest-remainder reading is the one implemented here; but the
   "the classic allocate operation from Martin Fowler's Money pattern" framing
   is inaccurate about what that operation does.
2. The standard (Wikipedia, largest remainder) explicitly does NOT specify a
   tie-break; the lowest-index rule comes from SPEC.md alone.  That is a
   legitimate specification choice, not a contradiction.
3. Which ValueError message wins when several validation rules break at once
   is left open (only the type is asserted here).
4. `bool` in `weights` is left accepted as 0/1 (bool is a subclass of int);
   SPEC.md does not say otherwise.
5. Non-integer or non-list inputs are outside the SPEC's stated domain and are
   not probed.
""".strip()


def _validate(weights) -> None:
    if len(weights) == 0:
        raise ValueError("weights is empty: there is no payee to allocate to")
    for i, w in enumerate(weights):
        if w < 0:
            raise ValueError(f"weights[{i}] is negative: a payee cannot hold a negative claim")
    if sum(weights) == 0:
        raise ValueError("every weight is zero: there is no basis on which to divide")


def _pick_by_brute_force(remainders, candidates, leftover):
    """Return the set of indices that receives one extra unit each.

    Maximises the summed fractional remainder; among equally good sets the
    lexicographically smallest sorted index tuple wins, which is precisely
    "largest remainder first, ties to the lowest index".
    """
    best_combo = None
    best_sum = None
    for combo in combinations(candidates, leftover):
        total = sum((remainders[i] for i in combo), Fraction(0))
        if best_sum is None or total > best_sum:
            best_sum, best_combo = total, combo
        # combinations() yields in lexicographic order, so an equal-sum combo
        # seen later is never lexicographically smaller: nothing to do on ties.
    return set(best_combo)


def _pick_greedy(remainders, candidates, leftover):
    """Fallback with the same semantics: repeated strict-max linear scan."""
    pool = list(candidates)
    chosen = set()
    for _ in range(leftover):
        best = None
        for i in pool:
            if best is None or remainders[i] > remainders[best]:
                best = i  # strict '>' keeps the earliest index on a tie
        chosen.add(best)
        pool.remove(best)
    return chosen


def oracle(total_cents, weights):
    _validate(weights)

    n = len(weights)
    magnitude = abs(total_cents)
    denominator = sum(weights)

    floors = []
    remainders = []
    for w in weights:
        claim = Fraction(magnitude * w, denominator)
        whole = math.floor(claim)
        floors.append(whole)
        remainders.append(claim - whole)

    leftover = magnitude - sum(floors)
    if leftover:
        candidates = [i for i in range(n) if remainders[i] > 0]
        if leftover > len(candidates):  # cannot happen; guard the invariant
            raise AssertionError("leftover exceeds the payees with a remainder")
        count = math.comb(len(candidates), leftover)
        picker = _pick_by_brute_force if count <= 200_000 else _pick_greedy
        for i in picker(remainders, candidates, leftover):
            floors[i] += 1

    if total_cents < 0:
        return [-x for x in floors]
    return floors


KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # Wikipedia, largest remainder method: the article's own worked table
    # (11 seats; Whites, Reds and Blues take the three surplus seats).
    ((11, [47000, 16000, 15800, 12000, 6100, 3100]), {}, [5, 2, 2, 1, 1, 0]),
    # Fowler, Money pattern: five cents split two ways is three and two.
    ((5, [1, 1]), {}, [3, 2]),
    # SPEC worked example, and a plain Hamilton apportionment (W = 7).
    ((10, [1, 2, 4]), {}, [1, 3, 6]),
    # Hamilton apportionment, W = 1000: quotas 40.4 / 39.7 / 19.9.
    ((100, [404, 397, 199]), {}, [40, 40, 20]),
    # Exact three-way remainder tie -> lowest index takes the unit.
    ((100, [1, 1, 1]), {}, [34, 33, 33]),
    # Four-way tie, one leftover.
    ((25, [1, 1, 1, 1]), {}, [7, 6, 6, 6]),
    # Zero-weight payee gets exactly zero; the tie goes to the lower index.
    ((11, [0, 1, 1]), {}, [0, 6, 5]),
    # Exact division: no leftover to hand out at all.
    ((100, [1, 1, 1, 1]), {}, [25, 25, 25, 25]),
    # Sign factored out first: the mirror of [3, 2], not [-2, -3].
    ((-5, [1, 1]), {}, [-3, -2]),
    # Negative form of the worked example.
    ((-10, [1, 2, 4]), {}, [-1, -3, -6]),
    # Negative with a zero-weight payee.
    ((-11, [0, 1, 1]), {}, [0, -6, -5]),
    # Zero total allocates all zeros.
    ((0, [1, 2, 3]), {}, [0, 0, 0]),
    # Validation, and it happens before any allocation (total may be 0).
    ((100, []), {}, ("raises", "ValueError")),
    ((0, []), {}, ("raises", "ValueError")),
    ((100, [1, -1, 2]), {}, ("raises", "ValueError")),
    ((0, [0, 0, 0]), {}, ("raises", "ValueError")),
]
