"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the
reference on each input, and keeps the first input where they disagree.

The generator is domain-aware on purpose.  A uniformly random date in
0001..9999 lands in the middle of some month roughly 97% of the time, where
every plausible implementation agrees.  The whole of ISO-8601 week numbering
only bites in the twelve or so days straddling New Year, so the distribution is
heavily biased there: the 27 Dec .. 6 Jan window, then the wider late-December
and early-January tails, then the 53-week years, then month and leap-day edges,
then a small tail of out-of-range dates that must raise ``ValueError``.
"""

from __future__ import annotations

import random

# Years whose week-numbering year has 53 weeks (Jan 1 is a Thursday, or the
# year is a leap year whose Jan 1 is a Wednesday).  These are where week 53
# actually exists and where off-by-one week numbering shows up.
LONG_YEARS = [1976, 1981, 1982, 1987, 1992, 1998, 2004, 2009, 2015, 2020, 2026]

# Years whose 1 January is each possible weekday, so the "first Thursday" rule
# is exercised in all seven configurations.
MIXED_YEARS = [2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017]

_MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    if month == 2 and _is_leap(year):
        return 29
    return _MONTH_LENGTHS[month - 1]


def _new_year_window(rng: random.Random) -> tuple[int, int, int]:
    """A date in the 27 Dec .. 6 Jan window around a boundary."""
    # ``year - 1`` is always >= 1: every listed year is modern and the random
    # fallback starts at 2.
    year = rng.choice(LONG_YEARS + MIXED_YEARS + [rng.randint(2, 9999)])
    offset = rng.randint(-5, 6)  # -5 -> 26 Dec of year-1, 6 -> 6 Jan of year
    if offset <= 0:
        return (year - 1, 12, 31 + offset)
    return (year, 1, offset)


def _december_or_january(rng: random.Random) -> tuple[int, int, int]:
    year = rng.choice(MIXED_YEARS + LONG_YEARS + [rng.randint(1, 9999)])
    if rng.random() < 0.5:
        return (year, 12, rng.randint(18, 31))
    return (year, 1, rng.randint(1, 14))


def _month_edge(rng: random.Random) -> tuple[int, int, int]:
    year = rng.choice([1, 4, 100, 400, 1900, 2000, 2023, 2024, 9999, rng.randint(1, 9999)])
    month = rng.randint(1, 12)
    limit = _days_in_month(year, month)
    return (year, month, rng.choice([1, 2, limit - 1, limit]))


def _uniform(rng: random.Random) -> tuple[int, int, int]:
    year = rng.randint(1, 9999)
    month = rng.randint(1, 12)
    return (year, month, rng.randint(1, _days_in_month(year, month)))


def _invalid(rng: random.Random) -> tuple[int, int, int]:
    kind = rng.randrange(5)
    if kind == 0:
        return (rng.choice([0, -1, 10000, 100000]), 1, 1)
    if kind == 1:
        return (2021, rng.choice([0, 13, -3, 100]), 15)
    if kind == 2:
        return (2021, rng.choice([1, 3, 5, 7, 8, 10, 12]), rng.choice([0, 32, -4]))
    if kind == 3:
        return (2021, rng.choice([4, 6, 9, 11]), 31)
    return (rng.choice([1900, 2021, 2023, 2100]), 2, rng.choice([29, 30]))


def sample(rng: random.Random) -> tuple[tuple, dict]:
    roll = rng.random()
    if roll < 0.42:
        args = _new_year_window(rng)
    elif roll < 0.62:
        args = _december_or_january(rng)
    elif roll < 0.76:
        args = _month_edge(rng)
    elif roll < 0.92:
        args = _uniform(rng)
    else:
        args = _invalid(rng)
    return args, {}


# Inputs that are always tried first, before random sampling.  These encode the
# corners the standard calls out by name, plus the invalid dates that must raise.
SEEDS: list[tuple[tuple, dict]] = [
    ((2021, 1, 1), {}),      # Friday -> (2020, 53, 5): week year precedes calendar year
    ((2021, 1, 3), {}),      # Sunday, last day of 2020-W53
    ((2021, 1, 4), {}),      # Monday -> (2021, 1, 1): week 1 holds 4 January
    ((2019, 12, 30), {}),    # Monday -> (2020, 1, 1): week year follows calendar year
    ((2020, 12, 28), {}),    # Monday that opens week 53 of a 53-week year
    ((2007, 1, 1), {}),      # 1 January is itself a Monday -> (2007, 1, 1)
    ((2007, 12, 31), {}),    # Monday -> (2008, 1, 1)
    ((2009, 12, 31), {}),    # Thursday -> (2009, 53, 4), the worked example
    ((1977, 1, 1), {}),      # Saturday -> (1976, 53, 6)
    ((2024, 2, 29), {}),     # leap day of a leap year
    ((1, 1, 1), {}),         # earliest supported date, a Monday -> (1, 1, 1)
    ((9999, 12, 31), {}),    # latest supported date -> (9999, 52, 5)
    ((2023, 2, 29), {}),     # invalid: 2023 is not a leap year
    ((1900, 2, 29), {}),     # invalid: century that is not divisible by 400
    ((2021, 13, 1), {}),     # invalid: month out of range
    ((0, 1, 1), {}),         # invalid: year below the supported range
]
