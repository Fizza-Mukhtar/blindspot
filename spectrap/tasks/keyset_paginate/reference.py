"""Reference implementation for FEED-2291 (keyset pagination over the feed).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: the seek method / "no offset" pagination technique,
https://use-the-index-luke.com/no-offset -- in particular its rule that the
cursor must carry the *whole* sort key, so that a non-unique leading column
cannot make a page boundary ambiguous.
"""

from __future__ import annotations

import re

# The wire format from the ticket: two non-empty runs of ASCII digits joined by
# a single colon.  Deliberately not int(): int() would accept "+1", " 12",
# "1_2" and non-ASCII digits, none of which we ever emit.
#
# `\Z`, not `$`.  Python's `$` also matches immediately before a single trailing
# newline, so `"200:9\n"` -- a cursor round-tripped through a line-oriented
# source -- would parse as valid and silently return the wrong page.  Found by
# the independent crosscheck oracle.
_CURSOR = re.compile(r"^([0-9]+):([0-9]+)\Z")


def _parse_cursor(cursor: str) -> tuple[int, int]:
    """Split a cursor into the (created_at, id) position it names."""
    if not isinstance(cursor, str):
        raise ValueError(f"malformed cursor: {cursor!r}")
    match = _CURSOR.match(cursor)
    if match is None:
        raise ValueError(f"malformed cursor: {cursor!r}")
    return int(match.group(1)), int(match.group(2))


def _sort_key(row: dict) -> tuple[int, int]:
    """The feed's sort key: the full tuple, never created_at alone."""
    return (row["created_at"], row["id"])


def page(
    rows: list[dict],
    cursor: str | None,
    limit: int,
) -> tuple[list[dict], str | None]:
    """Return one keyset page of the feed plus the cursor for the next one."""
    # Validate first: a bad argument never yields a partial page.
    if not isinstance(limit, int) or limit < 1:
        raise ValueError(f"limit must be an integer of at least 1, got {limit!r}")

    position = None if cursor is None else _parse_cursor(cursor)

    # The caller does not sort; we do.  created_at descending, id descending as
    # the tie-break -- one reverse=True over the pair gives both.
    ordered = sorted(rows, key=_sort_key, reverse=True)

    if position is not None:
        # The seek predicate.  Comparing the FULL tuple is the whole point: with
        # created_at alone, '<' drops the rest of a shared second and '<=' would
        # replay it.  Strict '<' on the pair is exact because ids are unique.
        ordered = [row for row in ordered if _sort_key(row) < position]

    page_rows = ordered[:limit]

    # None exactly when this page exhausted the candidates -- never hand back a
    # cursor whose only possible page is empty.
    if len(ordered) <= limit:
        return page_rows, None

    last = page_rows[-1]
    return page_rows, f"{last['created_at']}:{last['id']}"
