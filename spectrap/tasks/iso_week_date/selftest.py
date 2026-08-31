"""Authoritative examples for SCHED-208.

Every assertion here is traceable either to the cited definition of the
ISO-8601 week date or to an explicit sentence of SPEC.md -- never merely to
what the reference implementation happens to do.  ``make verify-corpus`` runs
this against ``reference.py`` in CI, which is what lets the README claim that
ground-truth labels are verified by construction rather than by inspection.

Source: https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar
"""

from datetime import date, timedelta

import pytest

import impl


def test_weekday_is_one_through_seven_with_monday_first():
    """Rule 2: weekday is 1..7, Monday = 1, Sunday = 7.

    2021-01-04 is a Monday and 2021-01-10 the Sunday that closes its week.
    """
    assert impl.to_iso_week_date(2021, 1, 4)[2] == 1
    assert impl.to_iso_week_date(2021, 1, 10)[2] == 7
    for offset in range(7):
        d = date(2021, 1, 4) + timedelta(days=offset)
        assert impl.to_iso_week_date(d.year, d.month, d.day)[2] == offset + 1


def test_weeks_run_monday_to_sunday_and_share_one_label():
    """Rule 1: a week is seven consecutive days beginning on a Monday.

    Mon 2020-12-28 .. Sun 2021-01-03 is one week, so all seven days carry the
    same (week_year, week_number) even though they straddle 1 January.
    """
    labels = []
    for offset in range(7):
        d = date(2020, 12, 28) + timedelta(days=offset)
        labels.append(impl.to_iso_week_date(d.year, d.month, d.day)[:2])
    assert labels == [(2020, 53)] * 7


def test_week_one_contains_four_january():
    """Rule 3: week 1 is the week containing 4 January."""
    for year in range(1900, 2101):
        assert impl.to_iso_week_date(year, 1, 4)[:2] == (year, 1)


def test_week_one_contains_the_first_thursday_of_the_year():
    """Rule 3, stated the other way round: week 1 holds the year's first Thursday."""
    for year in range(1990, 2041):
        d = date(year, 1, 1)
        while impl.to_iso_week_date(d.year, d.month, d.day)[2] != 4:
            d += timedelta(days=1)
        assert d.year == year  # the first Thursday is in January by construction
        assert impl.to_iso_week_date(d.year, d.month, d.day)[:2] == (year, 1)


def test_january_can_belong_to_the_previous_week_year():
    """Rule 4, and the first consequence spelled out in SPEC.md."""
    assert impl.to_iso_week_date(2021, 1, 1) == (2020, 53, 5)


def test_december_can_belong_to_the_next_week_year():
    """Rule 4, and the second consequence spelled out in SPEC.md."""
    assert impl.to_iso_week_date(2019, 12, 30) == (2020, 1, 1)


@pytest.mark.parametrize(
    "year,month,day,expected",
    [
        (1977, 1, 1, (1976, 53, 6)),    # Saturday in week 53 of the previous year
        (1978, 1, 1, (1977, 52, 7)),    # Sunday in week 52 of the previous year
        (1978, 1, 2, (1978, 1, 1)),     # the Monday that starts 1978-W01
        (1979, 12, 31, (1980, 1, 1)),   # Monday already in week 1 of the next year
        (1982, 1, 3, (1981, 53, 7)),    # Sunday closing a 53-week year
        (2005, 1, 2, (2004, 53, 7)),    # Sunday closing 2004-W53
        (2007, 1, 1, (2007, 1, 1)),     # 1 January is itself a Monday
        (2007, 12, 31, (2008, 1, 1)),   # Monday already in week 1 of 2008
        (2009, 12, 31, (2009, 53, 4)),  # the worked example in SPEC.md
    ],
)
def test_hand_checked_year_transitions(year, month, day, expected):
    """Rule 4: week_year is the year containing the week's Thursday."""
    assert impl.to_iso_week_date(year, month, day) == expected


def test_a_year_has_53_weeks_exactly_when_it_has_53_thursdays():
    """Rule 5: the week-numbering year is whole weeks, one Thursday each.

    The count of weeks in week-numbering year Y therefore equals the number of
    Thursdays in calendar year Y, which is 52 or 53.
    """
    for year in range(1950, 2051):
        thursdays = 0
        d = date(year, 1, 1)
        while d.year == year:
            if impl.to_iso_week_date(d.year, d.month, d.day)[2] == 4:
                thursdays += 1
            d += timedelta(days=1)
        assert thursdays in (52, 53)
        # The highest week number carrying this week_year must equal that count.
        highest = 0
        probe = date(year - 1, 12, 20) if year > 1 else date(year, 1, 1)
        while probe <= date(year, 12, 31) + timedelta(days=20):
            wy, wn, _ = impl.to_iso_week_date(probe.year, probe.month, probe.day)
            if wy == year:
                highest = max(highest, wn)
            probe += timedelta(days=1)
        assert highest == thursdays


def test_2020_is_a_53_week_year_and_2021_is_a_52_week_year():
    """Rule 5, using the two years SPEC.md names explicitly."""
    assert impl.to_iso_week_date(2020, 12, 31)[:2] == (2020, 53)
    assert impl.to_iso_week_date(2021, 1, 3)[:2] == (2020, 53)
    assert impl.to_iso_week_date(2021, 12, 31)[:2] == (2021, 52)
    assert impl.to_iso_week_date(2022, 1, 2)[:2] == (2021, 52)


def test_week_number_is_never_zero_and_never_above_53():
    """Rule 5: week_number is always in 1..53."""
    d = date(1995, 1, 1)
    while d <= date(2035, 12, 31):
        _, week, _ = impl.to_iso_week_date(d.year, d.month, d.day)
        assert 1 <= week <= 53
        d += timedelta(days=1)


def test_leap_day_is_accepted_and_placed():
    """SPEC.md 'Errors': 2024-02-29 returns (2024, 9, 4)."""
    assert impl.to_iso_week_date(2024, 2, 29) == (2024, 9, 4)
    assert impl.to_iso_week_date(2000, 2, 29)[:2] == (2000, 9)


def test_supported_extremes_do_not_raise():
    """SPEC.md 'Errors': the two endpoints of the supported range."""
    assert impl.to_iso_week_date(1, 1, 1) == (1, 1, 1)
    assert impl.to_iso_week_date(9999, 12, 31) == (9999, 52, 5)


@pytest.mark.parametrize(
    "year,month,day",
    [
        (0, 1, 1),        # year below range
        (-1, 6, 15),      # negative year
        (10000, 1, 1),    # year above range
        (2021, 0, 10),    # month below range
        (2021, 13, 10),   # month above range
        (2021, 1, 0),     # day below range
        (2021, 1, 32),    # day above range for a 31-day month
        (2021, 4, 31),    # April has 30 days
        (2023, 2, 29),    # 2023 is not a leap year
        (1900, 2, 29),    # century not divisible by 400 is not a leap year
        (2100, 2, 29),    # likewise
    ],
)
def test_out_of_range_dates_raise_value_error(year, month, day):
    """SPEC.md 'Errors': out-of-range year, month or day raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(year, month, day)


def test_returns_a_tuple_of_three_ints():
    """SPEC.md signature: returns tuple[int, int, int]."""
    result = impl.to_iso_week_date(2021, 1, 1)
    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(isinstance(part, int) and not isinstance(part, bool) for part in result)


def test_matches_the_standard_library_over_a_multi_year_span():
    """Cross-check against date.isocalendar(), which implements the same rules.

    This lives in the test suite only: the ticket forbids the implementation
    itself from delegating to it, but it is the authoritative oracle here.
    """
    d = date(1995, 1, 1)
    end = date(2035, 12, 31)
    while d <= end:
        expected = tuple(d.isocalendar())
        assert impl.to_iso_week_date(d.year, d.month, d.day) == expected, d
        d += timedelta(days=1)
