from datetime import date


def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a proleptic Gregorian calendar date to an ISO-8601 week date.

    Returns a ``(week_year, week_number, weekday)`` triple where weeks run
    Monday (1) to Sunday (7) and week 1 is the week containing the first
    Thursday of the calendar year (equivalently, the week containing 4
    January). ``week_year`` is the week-numbering year, which can differ
    from the calendar ``year`` passed in for dates near the year boundary.

    Raises ``ValueError`` if the year, month, or day do not form a valid
    date in the range 0001-01-01 through 9999-12-31.
    """
    # date() validates year (1..9999), month (1..12), and day (1..days-in-month)
    # for us, raising ValueError on anything out of range.
    given = date(year, month, day)

    # Monday=1 .. Sunday=7 (date.weekday() is Monday=0 .. Sunday=6).
    weekday = given.weekday() + 1

    # The Thursday of the Monday-Sunday week containing `given` determines
    # which calendar year the whole week belongs to.
    thursday_ordinal = given.toordinal() - weekday + 4
    thursday = date.fromordinal(thursday_ordinal)
    week_year = thursday.year

    # Week 1 of week_year is the week containing 4 January of that year;
    # find that week's Thursday the same way.
    jan4 = date(week_year, 1, 4)
    jan4_weekday = jan4.weekday() + 1
    week1_thursday_ordinal = jan4.toordinal() - jan4_weekday + 4

    week_number = (thursday_ordinal - week1_thursday_ordinal) // 7 + 1

    return (week_year, week_number, weekday)
