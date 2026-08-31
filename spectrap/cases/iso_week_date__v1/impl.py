"""SCHED-208: Convert a calendar date to an ISO-8601 week date.

The week-date arithmetic (finding the Thursday of a date's week, locating
week 1 via 4 January, and counting whole weeks between them) is implemented
explicitly here rather than delegated to date.isocalendar() or strftime, so
it can be ported line for line to other languages/engines.
"""

from datetime import date


def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a proleptic-Gregorian calendar date to an ISO-8601 week date.

    Returns (week_year, week_number, weekday), where weekday is 1 (Monday)
    through 7 (Sunday), week_number is 1..53, and week_year is the
    week-numbering year (the year containing the Thursday of that week).

    Raises ValueError if year is outside 1..9999, month is outside 1..12,
    or day is outside the valid range for that year/month.
    """
    d = date(year, month, day)  # validates year/month/day ranges for us

    ordinal = d.toordinal()
    weekday = d.weekday() + 1  # Monday=1 .. Sunday=7

    # The Thursday of the same Mon-Sun week as d. Its calendar year is,
    # by definition, the ISO week-numbering year for d.
    thursday_ordinal = ordinal + (4 - weekday)
    week_year = date.fromordinal(thursday_ordinal).year

    # Week 1 of week_year is the week containing 4 January of that year;
    # find the Thursday of that week the same way.
    jan4_ordinal = date(week_year, 1, 4).toordinal()
    jan4_weekday = date.fromordinal(jan4_ordinal).weekday() + 1
    week1_thursday_ordinal = jan4_ordinal + (4 - jan4_weekday)

    week_number = (thursday_ordinal - week1_thursday_ordinal) // 7 + 1

    return week_year, week_number, weekday
