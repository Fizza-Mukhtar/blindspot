"""Reference implementation for SCHED-208 (calendar date -> ISO-8601 week date).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: the ISO-8601 week date, as worded in the Python documentation for
``date.isocalendar()``:
https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar

Deliberately computed from first principles.  ``datetime.date`` is used only as
a day-number oracle (``toordinal`` / ``fromordinal``); ``isocalendar()``,
``weekday()`` and ``strftime`` are never called, because the ticket asks for
logic that can be ported to Kotlin and to SQL.
"""

from __future__ import annotations

from datetime import date

_MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

MIN_YEAR = 1
MAX_YEAR = 9999


def _is_leap_year(year: int) -> bool:
    """Proleptic Gregorian leap rule: /4, except /100, except /400."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    if month == 2 and _is_leap_year(year):
        return 29
    return _MONTH_LENGTHS[month - 1]


def _validate(year: int, month: int, day: int) -> None:
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f"year {year} is out of range {MIN_YEAR}..{MAX_YEAR}")
    if not 1 <= month <= 12:
        raise ValueError(f"month {month} is out of range 1..12")
    limit = _days_in_month(year, month)
    if not 1 <= day <= limit:
        raise ValueError(
            f"day {day} is out of range 1..{limit} for month {month} of year {year}"
        )


def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Return ``(week_year, week_number, weekday)`` for a Gregorian date."""
    _validate(year, month, day)

    ordinal = date(year, month, day).toordinal()

    # Rules 1 and 2: weeks run Monday..Sunday and the weekday is 1..7 with
    # Monday = 1.  Ordinal 1 is 0001-01-01, which is a Monday, so the residue
    # of (ordinal - 1) mod 7 is 0 exactly on Mondays.
    weekday = (ordinal - 1) % 7 + 1

    # Rule 4: a whole week belongs to the year containing its Thursday.  Step
    # from this date to the Thursday of its own Monday..Sunday week (Thursday
    # is weekday 4) and read the calendar year off that day.  The shift is at
    # most +3/-3 days, so it can never leave the supported ordinal range: the
    # earliest date is a Monday (shift +3) and the latest is a Friday (-1).
    thursday = ordinal + (4 - weekday)
    week_year = date.fromordinal(thursday).year

    # Rule 3: week 1 is the week holding the first Thursday of ``week_year``.
    # Every Thursday of that week-numbering year is therefore an exact multiple
    # of seven days after that first Thursday, so counting whole weeks from
    # 1 January of ``week_year`` numbers the weeks consecutively from 1.
    january_first = date(week_year, 1, 1).toordinal()
    week_number = (thursday - january_first) // 7 + 1

    return (week_year, week_number, weekday)
