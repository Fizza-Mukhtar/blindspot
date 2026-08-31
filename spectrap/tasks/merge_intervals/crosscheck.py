"""Independent oracle for SCHED-207 (merge_bookings).

Written WITHOUT reading reference.py or selftest.py.  Derived from SPEC.md plus
the half-open interval convention argued in EWD 831.
"""

from __future__ import annotations

ORACLE_NOTES = """\
Basis
-----
Grounding standard: E. W. Dijkstra, EWD 831, "Why numbering should start at
zero" (https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD831.html).
The two clauses of EWD 831 that actually decide this task:

  * Convention (a), `a <= i < b` -- the half-open form -- is preferred because
    "the difference between the bounds as mentioned equals the length of the
    subsequence", and because with it *adjacent subsequences share a boundary
    value*: the upper bound of one is the lower bound of the next.  That is the
    clause that makes [60,120) and [120,180) contiguous with no free minute
    between them, so they must coalesce into [60,180).  Conversely a gap in the
    output requires a strictly free value, so [60,120) and [121,180) stay apart
    (minute 120 belongs to no booking).

  * The empty-sequence clause: Dijkstra rejects including the upper bound
    because "inclusion of the upper bound would then force the latter to be
    unnatural by the time the sequence has shrunk to the empty one".  Under
    convention (a) the empty interval is exactly `a <= i < a`, i.e. start ==
    end.  A row with start == end therefore denotes the empty set of minutes --
    it covers nothing, so it can neither appear in the output nor bridge two
    blocks.  SPEC.md's "discard before any merging happens" is the operational
    restatement of that.

Oracle algorithm (deliberately NOT sort-and-sweep)
--------------------------------------------------
Set-theoretic brute force, which is the most literal possible reading of "every
minute that is covered by at least one non-empty input booking is covered by
exactly one output block, and no other minute is covered":

    covered = union over rows of set(range(start, end))
    output  = maximal runs of consecutive integers in sorted(covered)

`set(range(a, b))` IS the half-open convention -- Python's `range` is itself
built on `a <= i < b`, so the standard-library primitive supplies the semantics
rather than my re-deriving it.  Zero-length rows contribute `set(range(a, a))`
== the empty set for free, so the "drop cancellations first" requirement falls
out of the algebra instead of being a special case; no `<=` vs `<` comparison
appears anywhere in the oracle.

For pathologically wide spans (guard: > 4 million covered minutes, which the
generator never produces) it falls back to a coverage-counting sweep over a
delta map: +1 at each start, -1 at each end, blocks run from a 0 -> positive
transition to the return to 0.  Touching rows cancel their -1/+1 at the shared
boundary so the count never reaches zero there -- again no explicit adjacency
comparison.  The two paths were checked against each other on the seed corpus.

Validation
----------
All entries are validated in a full pass BEFORE any coverage is computed, so an
invalid row late in the list is always reported.  Shape errors and start > end
are both ValueError; the start > end message embeds the literal `(start, end)`
substring the ticket demands for grepping.

Ambiguities / possible defects noted in SPEC.md
-----------------------------------------------
1. `bool` is a subclass of `int` in Python, so `(True, False)` passes an
   `isinstance(x, int)` test.  SPEC.md says "either of its two elements is not
   an int" without saying whether a bool counts.  This oracle ACCEPTS bools as
   ints (plain isinstance).  The generator never emits bools so it cannot be
   settled differentially; it is genuinely under-determined.
2. Validation order between a shape-invalid row and a start > end row that both
   appear in the same input is unspecified: both raise ValueError, but which
   message wins is not pinned down.  This oracle validates left to right.
3. SPEC.md does not say whether a surviving unmerged booking may be the very
   tuple object handed in, or must be freshly built.  This oracle always builds
   fresh tuples, which satisfies either reading.
4. The `(120, 60)` message requirement is a *substring* requirement only; the
   rest of the message text is unconstrained.
5. SPEC.md types the parameter as `list[tuple[int, int]]` but says nothing about
   a non-list argument.  Observed: the reference duck-types the container (an
   iterator works, `None` gives TypeError); this oracle demands a list/tuple and
   gives ValueError.  Both readings are defensible; the input is out of contract.
6. Nothing in SPEC.md contradicts EWD 831.  The ticket's own worked example is
   consistent with the half-open reading throughout.

Differential result: 0 disagreements over the 16 generator SEEDS + 60k generated
samples + ~150k extra dense/wide-range samples from a second, independent
generator.  The only behavioural differences found are items 1 and 5 above, both
outside the SPEC's stated input domain.
"""

_BRUTE_FORCE_LIMIT = 4_000_000


def _validate(intervals):
    """Full validation pass.  Returns the list of (start, end) int pairs."""
    if not isinstance(intervals, (list, tuple)):
        raise ValueError(
            "intervals must be a list of (start, end) pairs, got "
            f"{type(intervals).__name__}"
        )
    rows = []
    for entry in intervals:
        if not isinstance(entry, (tuple, list)):
            raise ValueError(
                f"invalid booking row {entry!r}: expected a 2-element tuple or list"
            )
        if len(entry) != 2:
            raise ValueError(
                f"invalid booking row {entry!r}: expected exactly two elements, "
                f"got {len(entry)}"
            )
        start, end = entry[0], entry[1]
        for value in (start, end):
            if not isinstance(value, int):
                raise ValueError(
                    f"invalid booking row {entry!r}: endpoint {value!r} is not an int"
                )
        if start > end:
            raise ValueError(
                f"booking ends before it starts: ({start}, {end})"
            )
        rows.append((start, end))
    return rows


def _runs_from_covered(covered):
    """Maximal runs of consecutive integers, as half-open [start, end) tuples."""
    blocks = []
    run_start = None
    prev = None
    for minute in sorted(covered):
        if run_start is None:
            run_start = minute
        elif minute != prev + 1:
            blocks.append((run_start, prev + 1))
            run_start = minute
        prev = minute
    if run_start is not None:
        blocks.append((run_start, prev + 1))
    return blocks


def _sweep_by_coverage_count(rows):
    """Fallback: delta-map coverage counting.  No adjacency comparison at all."""
    delta = {}
    for start, end in rows:
        if start == end:  # empty set of minutes; contributes nothing
            continue
        delta[start] = delta.get(start, 0) + 1
        delta[end] = delta.get(end, 0) - 1
    blocks = []
    depth = 0
    block_start = None
    for point in sorted(delta):
        was_busy = depth > 0
        depth += delta[point]
        now_busy = depth > 0
        if not was_busy and now_busy:
            block_start = point
        elif was_busy and not now_busy:
            blocks.append((block_start, point))
            block_start = None
    return blocks


def oracle(*args, **kwargs):
    if kwargs:
        intervals = kwargs.pop("intervals", None)
        if kwargs:
            raise TypeError(f"unexpected keyword arguments: {sorted(kwargs)}")
        if args:
            raise TypeError("intervals given both positionally and by keyword")
    else:
        if len(args) != 1:
            raise TypeError(f"merge_bookings() takes 1 argument, got {len(args)}")
        intervals = args[0]

    rows = _validate(intervals)

    total = sum(end - start for start, end in rows)
    if total > _BRUTE_FORCE_LIMIT:
        return _sweep_by_coverage_count(rows)

    covered = set()
    for start, end in rows:
        covered.update(range(start, end))  # range() IS the half-open convention
    return _runs_from_covered(covered)


# Expected values derived from EWD 831 and SPEC.md, not from any implementation.
KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # Empty input -> empty list (SPEC.md, "Rules for the input").
    (([],), {}, []),
    # A lone booking survives verbatim.
    (([(60, 120)],), {}, [(60, 120)]),
    # EWD 831: adjacent subsequences share a boundary value -> contiguous.
    (([(60, 120), (120, 180)],), {}, [(60, 180)]),
    # One genuinely free minute (120) -> the boundary is real, blocks stay apart.
    (([(60, 120), (121, 180)],), {}, [(60, 120), (121, 180)]),
    # EWD 831's own worked subsequence 2..12 is 2 <= i < 13; abutting 13 <= i < 20
    # is the next subsequence, and together they cover 2..19 without a hole.
    (([(2, 13), (13, 20)],), {}, [(2, 20)]),
    # Empty interval (a <= i < a) covers nothing and must not bridge (SPEC.md).
    (([(0, 60), (90, 90), (120, 180)],), {}, [(0, 60), (120, 180)]),
    # Only a cancellation -> nothing is busy.
    (([(60, 60)],), {}, []),
    (([(0, 0), (0, 0), (1440, 1440)],), {}, []),
    # Exact duplicates are one block; nesting is absorbed.
    (([(60, 120), (60, 120)],), {}, [(60, 120)]),
    (([(60, 300), (120, 180)],), {}, [(60, 300)]),
    # Unsorted input must be sorted ascending by start on the way out.
    (([(300, 360), (60, 120), (120, 180)],), {}, [(60, 180), (300, 360)]),
    # Negative minutes; touching across midnight.
    (([(-60, 0), (0, 60)],), {}, [(-60, 60)]),
    (([(-120, -60), (-60, -60), (-30, 0)],), {}, [(-120, -60), (-30, 0)]),
    # Adjacency chain collapses to a single block.
    (([(0, 60), (60, 120), (120, 180), (180, 240)],), {}, [(0, 240)]),
    # A row handed over as a list is accepted; output is tuples.
    (([(0, 60), [60, 120]],), {}, [(0, 120)]),
    # The ticket's worked example.
    (
        ([(540, 600), (600, 630), (630, 630), (700, 720), (690, 700), (480, 540)],),
        {},
        [(480, 630), (690, 720)],
    ),
    # Errors.
    (([(120, 60)],), {}, ("raises", "ValueError")),
    (([(0, 60), (200, 100)],), {}, ("raises", "ValueError")),
    (([(0, 60, 90)],), {}, ("raises", "ValueError")),
    (([("60", 120)],), {}, ("raises", "ValueError")),
    (([(60.0, 120.0)],), {}, ("raises", "ValueError")),
    ((["nope"],), {}, ("raises", "ValueError")),
]
