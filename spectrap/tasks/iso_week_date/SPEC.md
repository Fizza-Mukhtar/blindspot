# SCHED-208 — Convert a calendar date to an ISO-8601 week date

**Component:** `scheduling/isoweek`
**Reporter:** Marek (Workforce Scheduling)
**Consumers:** the rota generator, the payroll export, the Kotlin mobile client

## Background

Our rota engine labels every shift with a week, and until now each service has
worked that label out for itself. The payroll export derives it from a
`strftime` format string, the web app derives it from a JavaScript date library,
and the Kotlin client derives it by dividing the day-of-year by seven. In the
last week of December they disagree, and last winter a night shift on
2019-12-30 was paid into the wrong week.

We are standardising on the ISO-8601 week date, and we need one canonical
implementation we can read, argue about, and then port line for line into
Kotlin and into a Postgres function. **So please write the calendar arithmetic
out explicitly. Do not delegate to `date.isocalendar()`, to `strftime` with
`%G`/`%V`/`%u`, or to any other library routine that already knows the answer —
we cannot port a delegation.** Using `datetime.date` for plain day arithmetic
(constructing a date, taking its ordinal, converting an ordinal back to a date)
is fine and expected; it is the week-date logic itself that must be ours.

## What to build

```python
def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    ...
```

The arguments are a date in the proleptic Gregorian calendar. Return the tuple
`(week_year, week_number, weekday)`.

## Rules

The governing definition is the ISO-8601 week date. The Python documentation
for `date.isocalendar()` states the same rules in the same words and is the
wording we are standardising on:
<https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar>

1. **Weeks run Monday to Sunday.** A week is seven consecutive days beginning
   on a Monday.
2. **`weekday` is 1 through 7, with Monday = 1 and Sunday = 7.** Not 0-based,
   and not Sunday-first.
3. **Week 1 is the week that contains the first Thursday of the calendar
   year** — equivalently, the week that contains 4 January. Weeks are then
   numbered consecutively from there.
4. **`week_year` is the week-numbering year, which is not always the same as
   the calendar year passed in.** Every week belongs entirely to the year that
   contains its Thursday. So the last few days of December can belong to week 1
   of the *following* year, and the first few days of January can belong to
   week 52 or 53 of the *previous* year. `week_year` is that year, not `year`.
5. **A week-numbering year has either 52 or 53 weeks**, because it is made of
   whole weeks and a calendar year contains either 52 or 53 Thursdays. 2020 has
   53 weeks; 2021 has 52. `week_number` is therefore always in `1..53`, and it
   is never 0.

Two consequences worth spelling out, because they are the ones that bite:

- `to_iso_week_date(2021, 1, 1)` is `(2020, 53, 5)`. 1 January 2021 is a
  Friday. Its week runs Mon 2020-12-28 to Sun 2021-01-03; that week's Thursday
  is 2020-12-31, so the whole week — including 1 January — belongs to week
  **53 of 2020**.
- `to_iso_week_date(2019, 12, 30)` is `(2020, 1, 1)`. 30 December 2019 is a
  Monday, its week's Thursday is 2020-01-02, so the week belongs to **2020**
  and, containing 4 January 2020, it is week **1**.

For the proleptic Gregorian calendar the leap rule applies uniformly to every
year in range: a year is a leap year when it is divisible by 4, except centuries,
which must be divisible by 400. 1900 has 28 days in February; 2000 has 29.

### Worked example

`to_iso_week_date(2009, 12, 31)`:

- 31 December 2009 is a Thursday, so `weekday` is 4.
- Its week is Mon 2009-12-28 … Sun 2010-01-03, whose Thursday is 2009-12-31,
  which falls in **2009**, so `week_year` is 2009.
- Week 1 of 2009 is the week containing the first Thursday of 2009
  (2009-01-01), i.e. Mon 2008-12-29 … Sun 2009-01-04. Counting whole weeks from
  there to the week of 2009-12-31 gives week **53**.
- Result: `(2009, 53, 4)`.

## Errors

Supported range is 1 January of year 1 through 31 December of year 9999,
matching the range the rest of our date handling already accepts.

Raise `ValueError` if `year` is outside `1..9999`, if `month` is outside
`1..12`, or if `day` is outside `1..n` where `n` is the number of days in that
month of that year. `to_iso_week_date(2023, 2, 29)` raises; `to_iso_week_date(2024, 2, 29)`
returns `(2024, 9, 4)`.

Valid extremes must not raise: `to_iso_week_date(1, 1, 1)` returns `(1, 1, 1)`
(0001-01-01 is a Monday in the proleptic Gregorian calendar) and
`to_iso_week_date(9999, 12, 31)` returns `(9999, 52, 5)`.

## Out of scope

- Parsing or formatting the `YYYY-Www-D` string form. We only need the triple.
- Time of day, time zones, and any notion of "now". The function is pure and
  takes every input as an argument.
- The ISO ordinal date (`YYYY-DDD`) — a separate ticket.
- Non-integer arguments. Callers are typed; assume three `int`s.
