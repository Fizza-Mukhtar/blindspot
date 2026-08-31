# SCHED-208 — Convert a calendar date to an ISO-8601 week date

**Component:** `scheduling/isoweek`
**Reporter:** Marek (Workforce Scheduling)
**Consumers:** the rota generator, the payroll export, the Kotlin mobile client

## Background

Each service works out its own week label and in late December they disagree; a
night shift on 2019-12-30 got paid into the wrong week. We're standardising on
the ISO-8601 week date and need one implementation we can port line for line into
Kotlin and Postgres, so write the calendar arithmetic out explicitly: no
`date.isocalendar()`, no `strftime` with `%G`/`%V`/`%u`, no library routine that
already knows the answer. Plain day arithmetic on `datetime.date` is fine; it's
the week-date logic itself that has to be ours.

## What to build

```python
def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    ...
```

Dates are proleptic Gregorian, so the leap rule applies uniformly across the
range: divisible by 4, except centuries, which need 400 (1900 is not a leap
year, 2000 is). Return `(week_year, week_number, weekday)`.

Follow the ISO-8601 week date as worded for `date.isocalendar()`
(<https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar>).
Briefly: a week is seven consecutive days running Monday to Sunday, `weekday`
numbers them 1 through 7 with Monday 1 and Sunday 7, and week 1 is the week
holding the year's first Thursday — equivalently the week holding 4 January —
with the rest numbered consecutively from there. Since a week is never split
between two years but belongs entirely to the year containing its Thursday,
`week_year` is that year rather than necessarily the `year` argument, which is
how late December lands in week 1 of the following year and early January in
week 52 or 53 of the preceding one: `to_iso_week_date(2021, 1, 1)` is
`(2020, 53, 5)` and `to_iso_week_date(2019, 12, 30)` is `(2020, 1, 1)`. A
week-numbering year is built of whole weeks and a calendar year holds 52 or
53 Thursdays, so `week_number` is always in `1..53` and never 0. 2020 has 53
weeks; 2021 has 52.

## Errors

Supported range is 0001-01-01 through 9999-12-31. Raise `ValueError` when `year`
is outside `1..9999`, `month` outside `1..12`, or `day` outside `1..n` for that
month of that year — `to_iso_week_date(2023, 2, 29)` raises,
`to_iso_week_date(2024, 2, 29)` returns `(2024, 9, 4)`. The extremes must not
raise: `to_iso_week_date(1, 1, 1)` is `(1, 1, 1)` and
`to_iso_week_date(9999, 12, 31)` is `(9999, 52, 5)`.

## Out of scope

The `YYYY-Www-D` string form; time of day, time zones and any notion of "now" —
the function is pure; the ISO ordinal date `YYYY-DDD`, a separate ticket;
non-integer arguments, since callers are typed.
