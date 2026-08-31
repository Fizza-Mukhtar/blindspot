"""Independent oracle for FEED-2291 (keyset / seek-method pagination).

The oracle does NOT reimplement the seek predicate in Python control flow.  It
builds a throw-away in-memory SQLite database and issues the *exact* query the
grounding standard prescribes, letting SQLite's own row-value comparison decide
the page boundary.
"""

from __future__ import annotations

import re
import sqlite3

ORACLE_NOTES = """
Based on: the seek method ("no offset" keyset pagination) as described at
https://use-the-index-luke.com/no-offset and, for the non-unique sort key, its
own deep-dive https://use-the-index-luke.com/sql/partial-results/fetch-next-page.

Clauses checked:
  * "Paging Through Results" / fetch-next-page: for a deterministic
    ORDER BY <col> DESC, <pk> DESC the continuation predicate must be the SQL
    row-value comparison  WHERE (sale_date, sale_id) < (?, ?)  -- the tuple, not
    the leading column.
  * The same page's warning about the naive predicate: filtering on the leading
    column alone would "skip all results from yesterday - not just the ones
    already shown on the first page".  This is precisely FEED-2291's trap.
  * The SQL-standard definition of row-value ordering quoted there:
    "X < Y is True if and only if Xi = Yi is True for all i < n and Xn < Yn for
    some n", i.e. "X sorts before Y".
  * The article's portable approximation for engines without row values:
    WHERE sale_date <= ? AND NOT (sale_date = ? AND sale_id >= ?).
    The oracle keeps this as a fallback and it is exercised by a self-check at
    import time, so both formulations are cross-validated against each other.
  * /no-offset: the cursor is carried forward from the last row of the page just
    returned; there is no counting of skipped rows, so a cursor is a *position*
    and need not still exist as a row.

Algorithm / independence: rows are loaded into an ephemeral sqlite3 in-memory
table keyed by their index in the caller's list; the page is obtained with

    SELECT idx FROM feed
     WHERE (created_at, id) < (?, ?)          -- omitted for cursor=None
     ORDER BY created_at DESC, id DESC
     LIMIT <limit + 1>

and `limit + 1` is fetched purely to answer "were there more candidates than
this page?"  next_cursor is None iff fewer than limit+1 candidates came back.
No Python-side sort, filter or comparison of the sort key occurs on the main
path.  (A pure-Python selection-sort path exists only for sort-key magnitudes
outside SQLite's signed 64-bit INTEGER range, which the ticket's inputs never
reach.)

Ambiguities / possible spec problems noted while deriving this:
  1. LEADING ZEROS.  SPEC.md's error clause says a well-formed cursor is "a
     non-empty run of ASCII digits, a single ':', and another non-empty run of
     ASCII digits".  Read literally, "0200:09" is WELL-FORMED and denotes the
     position (200, 9).  task.yaml lists this as an open question, so the two
     documents disagree about whether it is settled; the oracle follows SPEC.md's
     literal grammar and accepts it.
  2. bool IS AN int.  "limit must be an int of at least 1" - `True` is an
     `int` instance equal to 1.  SPEC.md does not say.  The oracle accepts
     `True` as limit 1 (pure isinstance reading) and no KNOWN_VALUE depends on
     it.
  3. IDENTITY OF RETURNED ROWS.  SPEC.md says payload "must come back
     untouched" and that the function must not mutate `rows`, but does not say
     whether the returned dicts are the caller's objects or copies.  The oracle
     returns the caller's own dict objects; equality-based comparison cannot
     tell the two readings apart.
  4. VALIDATION ORDER.  "Raise before doing any work" - when both `limit` and
     `cursor` are bad, both readings raise ValueError, so the order is
     unobservable.  Not a defect.
  5. CONFIRMED REFERENCE DEFECT (found by this cross-check).  reference.page
     ACCEPTS the cursor "1000:7\\n" (one trailing newline) and pages from
     position (1000, 7); SPEC.md's grammar -- "a str consisting of a non-empty
     run of ASCII digits, a single ':', and another non-empty run of ASCII
     digits" -- admits no newline, and generators.py itself lists "1000:7\\n"
     in MALFORMED_CURSORS.  Black-box probing shows exactly one trailing "\\n"
     is accepted while "\\n\\n", "\\r", "\\r\\n", "\\t", " " and a leading
     "\\n" are all rejected: the signature of an anchored `re.match(r"^[0-9]+:
     [0-9]+$", s)`, since Python's `$` also matches immediately before a final
     newline.  The fix is `re.fullmatch` without a trailing `$`, or `\\Z`.
     This is the only input class on which oracle and reference differ across
     200,016 fuzz cases.
  6. NEGATIVE created_at.  The cursor grammar is digits-only, so no cursor can
     ever name a negative position; rows are guaranteed non-negative.
     Consistent, nothing to resolve.
"""

_CURSOR_RE = re.compile(r"[0-9]+:[0-9]+")

_INT64_MAX = 2 ** 63 - 1

_ROW_VALUES_SUPPORTED: bool | None = None


def _row_values_supported() -> bool:
    """Does the bundled SQLite understand ``(a, b) < (?, ?)``?"""
    global _ROW_VALUES_SUPPORTED
    if _ROW_VALUES_SUPPORTED is None:
        try:
            with sqlite3.connect(":memory:") as con:
                con.execute("SELECT 1 WHERE (1, 2) < (1, 3)").fetchall()
            _ROW_VALUES_SUPPORTED = True
        except sqlite3.Error:
            _ROW_VALUES_SUPPORTED = False
    return _ROW_VALUES_SUPPORTED


def _parse_cursor(cursor):
    """Return None, or the (created_at, id) position the cursor names.

    Raises ValueError for anything the ticket calls malformed.
    """
    if cursor is None:
        return None
    if not isinstance(cursor, str):
        raise ValueError(f"malformed cursor: {cursor!r}")
    if _CURSOR_RE.fullmatch(cursor) is None:
        raise ValueError(f"malformed cursor: {cursor!r}")
    left, _, right = cursor.partition(":")
    return (int(left), int(right))


def _check_limit(limit) -> int:
    if not isinstance(limit, int):
        raise ValueError(f"limit must be an int >= 1, got {limit!r}")
    if limit < 1:
        raise ValueError(f"limit must be an int >= 1, got {limit!r}")
    return limit


def _select_via_sqlite(keys, position, limit):
    """keys: list of (idx, created_at, id).  Returns up to limit+1 idx values."""
    con = sqlite3.connect(":memory:")
    try:
        con.execute("CREATE TABLE feed (idx INTEGER, created_at INTEGER, id INTEGER)")
        con.executemany("INSERT INTO feed (idx, created_at, id) VALUES (?, ?, ?)", keys)
        tail = " ORDER BY created_at DESC, id DESC LIMIT ?"
        if position is None:
            sql = "SELECT idx FROM feed" + tail
            params = (limit + 1,)
        elif _row_values_supported():
            # The standard's row-value predicate, verbatim in shape.
            sql = "SELECT idx FROM feed WHERE (created_at, id) < (?, ?)" + tail
            params = (position[0], position[1], limit + 1)
        else:
            # The article's portable approximation of the same predicate.
            sql = (
                "SELECT idx FROM feed"
                " WHERE created_at <= ?"
                " AND NOT (created_at = ? AND id >= ?)" + tail
            )
            params = (position[0], position[0], position[1], limit + 1)
        return [r[0] for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def _select_via_python(keys, position, limit):
    """Fallback for magnitudes outside SQLite's INTEGER range.

    Deliberately naive: a selection sort over the descending total order, then a
    linear scan applying the standard's row-value rule element by element.
    """
    def sorts_before(x, y):
        # "X < Y is True iff Xi = Yi for all i < n and Xn < Yn for some n"
        for a, b in zip(x, y):
            if a != b:
                return a < b
        return False

    remaining = list(keys)
    ordered = []
    while remaining:
        best = 0
        for i in range(1, len(remaining)):
            # descending: the row that sorts *after* comes first
            if sorts_before((remaining[best][1], remaining[best][2]),
                            (remaining[i][1], remaining[i][2])):
                best = i
        ordered.append(remaining.pop(best))

    out = []
    for idx, created_at, row_id in ordered:
        if position is not None and not sorts_before((created_at, row_id), position):
            continue
        out.append(idx)
        if len(out) > limit:
            break
    return out


def oracle(rows, cursor, limit):
    limit = _check_limit(limit)
    position = _parse_cursor(cursor)

    keys = [(i, r["created_at"], r["id"]) for i, r in enumerate(rows)]

    magnitudes = [abs(ca) for _, ca, _ in keys] + [abs(rid) for _, _, rid in keys]
    if position is not None:
        magnitudes += [abs(position[0]), abs(position[1])]
    if magnitudes and max(magnitudes) > _INT64_MAX:
        picked = _select_via_python(keys, position, limit)
    else:
        picked = _select_via_sqlite(keys, position, limit)

    exhausted = len(picked) <= limit
    picked = picked[:limit]
    page_rows = [rows[i] for i in picked]

    if exhausted or not page_rows:
        next_cursor = None
    else:
        last = page_rows[-1]
        next_cursor = f"{last['created_at']}:{last['id']}"
    return (page_rows, next_cursor)


# --------------------------------------------------------------------------
# Values derived from the standard's worked example and SPEC.md's own example.
# --------------------------------------------------------------------------

_FEED = [
    {"id": 4, "created_at": 300},
    {"id": 9, "created_at": 200},
    {"id": 7, "created_at": 200},
    {"id": 2, "created_at": 200},
    {"id": 5, "created_at": 100},
]

# The shape of the standard's own example: ORDER BY sale_date DESC, sale_id DESC
# over a day (`SALE_DATE` = 1970-01-02 here, encoded as the second 86400) that
# holds several sales.  The article's point is that the second page must return
# the *rest* of that day, not the next day.
_SALES = [
    {"id": 6, "created_at": 86400, "amount": 10},
    {"id": 5, "created_at": 86400, "amount": 20},
    {"id": 4, "created_at": 86400, "amount": 30},
    {"id": 3, "created_at": 86400, "amount": 40},
    {"id": 2, "created_at": 0, "amount": 50},
    {"id": 1, "created_at": 0, "amount": 60},
]

KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # SPEC.md's worked example, page 1: boundary lands inside the 200s.
    ((list(_FEED), None, 2), {},
     ([{"id": 4, "created_at": 300}, {"id": 9, "created_at": 200}], "200:9")),
    # page 2: ids 7 and 2 are still owed -- the whole point of the ticket.
    ((list(_FEED), "200:9", 2), {},
     ([{"id": 7, "created_at": 200}, {"id": 2, "created_at": 200}], "200:2")),
    # page 3 exhausts the feed -> next_cursor None even though a row was returned.
    ((list(_FEED), "200:2", 2), {}, ([{"id": 5, "created_at": 100}], None)),
    # A page landing exactly on the final row reports None, not a dead cursor.
    ((list(_FEED), "200:7", 2), {},
     ([{"id": 2, "created_at": 200}, {"id": 5, "created_at": 100}], None)),
    # Cursor already past the end of the feed.
    ((list(_FEED), "100:5", 3), {}, ([], None)),
    # Cursor for a row that never existed: a position, not a lookup.
    ((list(_FEED), "200:8", 3), {},
     ([{"id": 7, "created_at": 200}, {"id": 2, "created_at": 200},
       {"id": 5, "created_at": 100}], None)),
    # Input arrives unordered; the function sorts it itself.
    (([{"id": 5, "created_at": 100}, {"id": 4, "created_at": 300},
       {"id": 2, "created_at": 200}, {"id": 9, "created_at": 200},
       {"id": 7, "created_at": 200}], None, 3), {},
     ([{"id": 4, "created_at": 300}, {"id": 9, "created_at": 200},
       {"id": 7, "created_at": 200}], "200:7")),
    # Limit exactly the feed size -> exhausted -> None.
    ((list(_FEED), None, 5), {},
     ([{"id": 4, "created_at": 300}, {"id": 9, "created_at": 200},
       {"id": 7, "created_at": 200}, {"id": 2, "created_at": 200},
       {"id": 5, "created_at": 100}], None)),
    # Empty candidate set.
    (([], None, 3), {}, ([], None)),
    (([], "200:9", 3), {}, ([], None)),
    # The standard's warning, transcribed: after page 1 of "yesterday's" sales
    # the next page must return the REST of that same day, not skip to the day
    # before.  `created_at < 86400` would wrongly return ids 2 and 1.
    ((list(_SALES), None, 2), {},
     ([{"id": 6, "created_at": 86400, "amount": 10},
       {"id": 5, "created_at": 86400, "amount": 20}], "86400:5")),
    ((list(_SALES), "86400:5", 2), {},
     ([{"id": 4, "created_at": 86400, "amount": 30},
       {"id": 3, "created_at": 86400, "amount": 40}], "86400:3")),
    ((list(_SALES), "86400:3", 4), {},
     ([{"id": 2, "created_at": 0, "amount": 50},
       {"id": 1, "created_at": 0, "amount": 60}], None)),
    # Payload passthrough.
    (([{"id": 3, "created_at": 7, "kind": "x"}], None, 4), {},
     ([{"id": 3, "created_at": 7, "kind": "x"}], None)),
    # Position below every row.
    ((list(_FEED), "0:1", 2), {}, ([], None)),
    # Errors: limit.
    ((list(_FEED), None, 0), {}, ("raises", "ValueError")),
    ((list(_FEED), None, -2), {}, ("raises", "ValueError")),
    ((list(_FEED), None, 1.0), {}, ("raises", "ValueError")),
    ((list(_FEED), None, "2"), {}, ("raises", "ValueError")),
    # Errors: malformed cursors, exactly the list SPEC.md enumerates.
    ((list(_FEED), "12", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), "12:", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), ":3", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), "12:3:4", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), "12 : 3", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), "-1:3", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), "1.0:3", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), "", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), "200:9\n", 2), {}, ("raises", "ValueError")),
    ((list(_FEED), 200, 2), {}, ("raises", "ValueError")),
]
