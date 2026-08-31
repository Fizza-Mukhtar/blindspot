"""Independent oracle for SCHED-208 (iso_week_date).

Deliberately structured differently from any hand-rolled calendar arithmetic:
the primary path delegates the whole week-date computation to the standard
library, which already implements the standard being cited.
"""

from __future__ import annotations

from datetime import MAXYEAR, MINYEAR, date

ORACLE_NOTES = (
    "Primary path: datetime.date.isocalendar(), i.e. the stdlib routine whose own "
    "documentation task.yaml names as the grounding standard. The ticket forbids the "
    "implementation from delegating to it; an oracle has no such restriction, and this "
    "is the standard's executable form. Secondary path (asserted equal on every call): "
    "an independent ordinal brute force -- 0001-01-01 is ordinal 1 and a Monday so "
    "weekday=((ord-1)%7)+1; the week's Thursday is ord+(4-weekday); week_year is that "
    "Thursday's Gregorian year; week 1 is found by scanning 1..7 Jan of week_year for "
    "the first Thursday, week=(thu-first_thu)//7+1. No constant or identity is shared "
    "between the paths. Clauses checked: 'a week starts on a Monday and ends on a "
    "Sunday'; 'the first (Gregorian) calendar week of a year containing a Thursday ... "
    "and the ISO year of that Thursday is the same as its Gregorian year'; 'the ISO "
    "year consists of 52 or 53 full weeks' (1<=week<=53 asserted); 'Monday is 1 and "
    "Sunday is 7'; MINYEAR=1/MAXYEAR=9999 for the supported range. Both worked examples "
    "in the cited text (2003-12-29 -> (2004,1,1); 2004-01-04 -> (2004,1,7)) are in "
    "KNOWN_VALUES. Range/leap validation is done explicitly here (div by 4, except "
    "centuries not div by 400) rather than inherited from date()'s own errors. "
    "SPEC.md findings: no contradiction with the standard -- every concrete value it "
    "asserts verifies against isocalendar(). Genuinely under-determined (matches "
    "task.yaml's open_questions, so by design not defects): plain tuple vs tuple "
    "subclass -- note isocalendar() itself returns datetime.IsoCalendarDate, a tuple "
    "subclass, so 'the Python docs are the wording we standardise on' does not settle "
    "it; and the ValueError message granularity. Also unspecified but unobservable: "
    "which field is reported first when several are out of range."
)

_MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap(year: int) -> bool:
    # Proleptic Gregorian leap rule, applied uniformly to every year in range.
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    if month == 2 and _is_leap(year):
        return 29
    return _MONTH_LENGTHS[month - 1]


def _bruteforce(d: date) -> tuple[int, int, int]:
    """Second, independent derivation working only in day ordinals."""
    ordinal = d.toordinal()
    # 0001-01-01 is ordinal 1 and is a Monday (proleptic Gregorian).
    weekday = ((ordinal - 1) % 7) + 1

    # The Thursday of this date's own week.
    thursday_ord = ordinal + (4 - weekday)
    week_year = date.fromordinal(thursday_ord).year

    # Brute-force scan for the first Thursday of that week-numbering year.
    first_thursday_ord = None
    for day in range(1, 8):
        candidate = date(week_year, 1, day)
        if ((candidate.toordinal() - 1) % 7) + 1 == 4:
            first_thursday_ord = candidate.toordinal()
            break
    assert first_thursday_ord is not None

    week_number = (thursday_ord - first_thursday_ord) // 7 + 1
    return (week_year, week_number, weekday)


def oracle(year: int, month: int, day: int) -> tuple[int, int, int]:
    if not (MINYEAR <= year <= MAXYEAR):
        raise ValueError(f"year {year!r} is out of range {MINYEAR}..{MAXYEAR}")
    if not (1 <= month <= 12):
        raise ValueError(f"month {month!r} is out of range 1..12")
    limit = _days_in_month(year, month)
    if not (1 <= day <= limit):
        raise ValueError(f"day {day!r} is out of range 1..{limit} for {year:04d}-{month:02d}")

    d = date(year, month, day)

    iso = d.isocalendar()
    primary = (int(iso[0]), int(iso[1]), int(iso[2]))

    secondary = _bruteforce(d)
    assert primary == secondary, (year, month, day, primary, secondary)

    # Structural invariants straight from the standard's text.
    assert 1 <= primary[1] <= 53
    assert 1 <= primary[2] <= 7
    return primary


# ---------------------------------------------------------------------------
# Values derived from the standard's own text and its worked examples.
# ---------------------------------------------------------------------------
KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # The two examples printed verbatim in the cited documentation:
    # "2004 begins on a Thursday, so the first week of ISO year 2004 begins on
    #  Monday, 29 Dec 2003 and ends on Sunday, 4 Jan 2004"
    ((2003, 12, 29), {}, (2004, 1, 1)),
    ((2004, 1, 4), {}, (2004, 1, 7)),
    # Clause 2 the other way round: the week holding 4 January is week 1.
    ((2021, 1, 4), {}, (2021, 1, 1)),
    # Week belongs to the year of its Thursday -> week year precedes calendar year.
    ((2021, 1, 1), {}, (2020, 53, 5)),
    ((2021, 1, 3), {}, (2020, 53, 7)),
    # ... and follows it.
    ((2019, 12, 30), {}, (2020, 1, 1)),
    ((2007, 12, 31), {}, (2008, 1, 1)),
    # "The ISO year consists of 52 or 53 full weeks": 2020 is a 53-week year.
    ((2020, 12, 28), {}, (2020, 53, 1)),
    ((2020, 12, 31), {}, (2020, 53, 4)),
    ((1977, 1, 1), {}, (1976, 53, 6)),
    # 1 January that is itself a Monday: week 1 starts on it.
    ((2007, 1, 1), {}, (2007, 1, 1)),
    # Sunday = 7 at a year boundary; 2000-01-01 is a Saturday in W52 of 1999.
    ((2000, 1, 1), {}, (1999, 52, 6)),
    # Proleptic Gregorian leap rule.
    ((2024, 2, 29), {}, (2024, 9, 4)),
    ((4, 2, 29), {}, (4, 9, 7)),
    ((1900, 1, 1), {}, (1900, 1, 1)),
    # date.min / date.max (MINYEAR = 1, MAXYEAR = 9999) must not raise.
    ((1, 1, 1), {}, (1, 1, 1)),
    ((9999, 12, 31), {}, (9999, 52, 5)),
    # Out-of-range inputs.
    ((2023, 2, 29), {}, ("raises", "ValueError")),
    ((1900, 2, 29), {}, ("raises", "ValueError")),
    ((2021, 4, 31), {}, ("raises", "ValueError")),
    ((2021, 13, 1), {}, ("raises", "ValueError")),
    ((2021, 0, 1), {}, ("raises", "ValueError")),
    ((2021, 1, 0), {}, ("raises", "ValueError")),
    ((0, 1, 1), {}, ("raises", "ValueError")),
    ((10000, 1, 1), {}, ("raises", "ValueError")),
    ((-1, 1, 1), {}, ("raises", "ValueError")),
]
