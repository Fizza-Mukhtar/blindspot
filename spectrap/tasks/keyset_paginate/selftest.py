"""Authoritative examples for FEED-2291.

Every assertion here is traceable to the cited technique or to an explicit
sentence of SPEC.md, not to the reference implementation's incidental
behaviour.  ``make verify-corpus`` runs this against ``reference.py`` in CI,
which is what lets the README claim that ground-truth labels are verified by
construction rather than by inspection.

Source: the seek method ("no offset" pagination),
https://use-the-index-luke.com/no-offset
"""

import pytest

import impl

# The ticket's worked example.  Three rows share the timestamp 200, which is
# where a cursor keyed on created_at alone stops being able to say where the
# previous page ended.
TIE_FEED = [
    {"id": 4, "created_at": 300},
    {"id": 9, "created_at": 200},
    {"id": 7, "created_at": 200},
    {"id": 2, "created_at": 200},
    {"id": 5, "created_at": 100},
]


def ids(rows):
    return [row["id"] for row in rows]


def test_rows_are_sorted_by_the_function_itself():
    """SPEC 'Feed order': created_at descending, then id descending, and 'the
    rows arrive in no particular order ... do not assume the caller sorted
    them'."""
    unordered = [
        {"id": 2, "created_at": 200},
        {"id": 5, "created_at": 100},
        {"id": 4, "created_at": 300},
        {"id": 9, "created_at": 200},
        {"id": 7, "created_at": 200},
    ]
    rows, _ = impl.page(unordered, None, 99)
    assert ids(rows) == [4, 9, 7, 2, 5]


def test_worked_example_first_page():
    """SPEC 'Worked example', first call."""
    rows, cursor = impl.page(TIE_FEED, None, 2)
    assert ids(rows) == [4, 9]
    assert cursor == "200:9"


def test_cursor_inside_a_tie_group_still_returns_the_rest_of_that_second():
    """The seek predicate of https://use-the-index-luke.com/no-offset applied to
    the full key: with cursor 200:9, rows 7 and 2 -- same created_at, smaller id
    -- are still owed to the caller.  Keying on created_at alone with '<' drops
    them."""
    rows, cursor = impl.page(TIE_FEED, "200:9", 2)
    assert ids(rows) == [7, 2]
    assert cursor == "200:2"


def test_cursor_does_not_replay_its_own_row_or_the_rest_of_the_group():
    """SPEC: rows are kept only when strictly after the cursor position;
    '<=' on created_at would replay the whole second forever."""
    rows, _ = impl.page(TIE_FEED, "200:9", 99)
    assert 9 not in ids(rows)
    assert ids(rows) == [7, 2, 5]


def test_full_walk_yields_every_row_exactly_once_in_feed_order():
    """SPEC: 'the union of all pages must be the whole feed, each row exactly
    once'.  Walked at limit 2, so a boundary falls inside the group stamped
    200."""
    seen = []
    cursor = None
    for _ in range(10):
        rows, cursor = impl.page(TIE_FEED, cursor, 2)
        seen.extend(rows)
        if cursor is None:
            break
    assert cursor is None
    assert ids(seen) == [4, 9, 7, 2, 5]


def test_full_walk_at_limit_one_also_covers_the_feed_exactly_once():
    """Same clause, with every page boundary inside the tie group."""
    seen = []
    cursor = None
    for _ in range(10):
        rows, cursor = impl.page(TIE_FEED, cursor, 1)
        seen.extend(rows)
        if cursor is None:
            break
    assert cursor is None
    assert ids(seen) == [4, 9, 7, 2, 5]


def test_next_cursor_is_none_when_the_page_exhausts_the_candidates():
    """SPEC 'Page size and the end of the feed': None exactly when limit
    candidates or fewer remained."""
    _, cursor = impl.page(TIE_FEED, "200:2", 2)
    assert cursor is None


def test_page_landing_exactly_on_the_last_row_reports_no_next_page():
    """SPEC: 'when a page lands exactly on the final row of the feed the answer
    is None; do not hand back a cursor that would only ever produce an empty
    page'."""
    rows, cursor = impl.page(TIE_FEED, None, 5)
    assert ids(rows) == [4, 9, 7, 2, 5]
    assert cursor is None


def test_next_cursor_is_the_last_row_of_the_page():
    """SPEC 'The cursor': built from the last row of the page just returned."""
    rows, cursor = impl.page(TIE_FEED, None, 3)
    last = rows[-1]
    assert cursor == f"{last['created_at']}:{last['id']}"
    assert cursor == "200:7"


def test_limit_larger_than_the_feed_returns_everything_and_no_cursor():
    """SPEC 'Page size and the end of the feed'."""
    rows, cursor = impl.page(TIE_FEED, None, 99)
    assert ids(rows) == [4, 9, 7, 2, 5]
    assert cursor is None


def test_cursor_for_a_deleted_row_still_positions_the_page():
    """SPEC 'The cursor': 'The cursor is a position, not a lookup' -- no row
    with id 8 exists, and paging continues from that position anyway."""
    rows, cursor = impl.page(TIE_FEED, "200:8", 3)
    assert ids(rows) == [7, 2, 5]
    assert cursor is None


def test_cursor_past_the_end_returns_an_empty_page():
    """SPEC: 'a cursor that has already run off the end of the feed' returns
    ([], None)."""
    assert impl.page(TIE_FEED, "100:5", 3) == ([], None)


def test_empty_feed_returns_empty_page_and_no_cursor():
    """SPEC 'Page size and the end of the feed'."""
    assert impl.page([], None, 3) == ([], None)
    assert impl.page([], "200:9", 3) == ([], None)


def test_payload_keys_survive_untouched():
    """SPEC 'What to build': other keys 'are payload and must come back
    untouched'."""
    feed = [{"id": 3, "created_at": 7, "kind": "comment", "body": "hi"}]
    rows, _ = impl.page(feed, None, 4)
    assert rows == [{"id": 3, "created_at": 7, "kind": "comment", "body": "hi"}]


def test_input_list_is_not_mutated():
    """SPEC 'Out of scope': 'The function is pure and must not mutate rows'."""
    feed = [
        {"id": 1, "created_at": 5},
        {"id": 2, "created_at": 9},
        {"id": 3, "created_at": 5},
    ]
    before = [dict(row) for row in feed]
    impl.page(feed, None, 2)
    assert feed == before
    assert ids(feed) == [1, 2, 3]


@pytest.mark.parametrize("bad", [0, -1, -100, 2.0, "3", None])
def test_bad_limit_raises_value_error(bad):
    """SPEC 'Errors': limit must be an int of at least 1."""
    with pytest.raises(ValueError):
        impl.page(TIE_FEED, None, bad)


@pytest.mark.parametrize(
    "bad",
    ["", "12", "12:", ":3", "12:3:4", "12 : 3", "-1:3", "1.0:3", "abc:3", 123, 12.5],
)
def test_malformed_cursor_raises_value_error(bad):
    """SPEC 'Errors': the well-formed shape is digits, one colon, digits; a
    non-string that is not None is malformed."""
    with pytest.raises(ValueError):
        impl.page(TIE_FEED, bad, 2)


def test_arguments_are_validated_before_any_page_is_produced():
    """SPEC 'Errors': 'Raise before doing any work; a bad argument never yields
    a partial page.'  An empty feed does not excuse a bad limit."""
    with pytest.raises(ValueError):
        impl.page([], None, 0)
