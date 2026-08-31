# SPEC.terse.md fairness audit — `iso_week_date` (SCHED-208)

Every assertion in `selftest.py` was checked against `SPEC.terse.md` alone, plus
the normative reference the ticket cites (the ISO-8601 week date as worded for
`datetime.date.isocalendar()`,
<https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar>).
15 test functions, covering 34 parametrised cases.

| selftest function | determined by | verdict |
| --- | --- | --- |
| `test_weekday_is_one_through_seven_with_monday_first` | "a week is seven consecutive days running Monday to Sunday, `weekday` numbers them 1 through 7 with Monday 1 and Sunday 7" | DETERMINED |
| `test_weeks_run_monday_to_sunday_and_share_one_label` | "a week is seven consecutive days running Monday to Sunday" fixes Mon 2020-12-28 … Sun 2021-01-03 as one week; "Since a week is never split between two years but belongs entirely to the year containing its Thursday, `week_year` is that year rather than necessarily the `year` argument" makes all seven days share one label; "`to_iso_week_date(2021, 1, 1)` is `(2020, 53, 5)`" fixes that label as `(2020, 53)` | DETERMINED |
| `test_week_one_contains_four_january` | "week 1 is the week holding the year's first Thursday — equivalently the week holding 4 January" | DETERMINED |
| `test_week_one_contains_the_first_thursday_of_the_year` | same sentence, read in its first form: "week 1 is the week holding the year's first Thursday" | DETERMINED |
| `test_january_can_belong_to_the_previous_week_year` | "`to_iso_week_date(2021, 1, 1)` is `(2020, 53, 5)`" (stated verbatim), and independently derivable from "belongs entirely to the year containing its Thursday" | DETERMINED |
| `test_december_can_belong_to_the_next_week_year` | "`to_iso_week_date(2019, 12, 30)` is `(2020, 1, 1)`" (stated verbatim) | DETERMINED |
| `test_hand_checked_year_transitions` (9 cases, incl. the 2009-12-31 → `(2009, 53, 4)` case) | derived from three sentences acting together: "a week is seven consecutive days running Monday to Sunday, `weekday` numbers them 1 through 7 with Monday 1 and Sunday 7, and week 1 is the week holding the year's first Thursday — equivalently the week holding 4 January — with the rest numbered consecutively from there" and "Since a week is never split between two years but belongs entirely to the year containing its Thursday, `week_year` is that year rather than necessarily the `year` argument". Each case is a mechanical consequence; no case needs a further choice | DETERMINED |
| `test_a_year_has_53_weeks_exactly_when_it_has_53_thursdays` | "A week-numbering year is built of whole weeks and a calendar year holds 52 or 53 Thursdays"; the one-Thursday-per-week correspondence that makes `highest == thursdays` comes from "belongs entirely to the year containing its Thursday" plus "with the rest numbered consecutively from there" | DETERMINED |
| `test_2020_is_a_53_week_year_and_2021_is_a_52_week_year` | "2020 has 53 weeks; 2021 has 52", plus the Thursday-ownership sentence to place 2020-12-31, 2021-01-03, 2021-12-31 and 2022-01-02 | DETERMINED |
| `test_week_number_is_never_zero_and_never_above_53` | "`week_number` is always in `1..53` and never 0" | DETERMINED |
| `test_leap_day_is_accepted_and_placed` | "`to_iso_week_date(2024, 2, 29)` returns `(2024, 9, 4)`" verbatim; 2000-02-29 exists by "divisible by 4, except centuries, which need 400 (1900 is not a leap year, 2000 is)" and its week follows from the week-1 and Monday-start rules | DETERMINED |
| `test_supported_extremes_do_not_raise` | "The extremes must not raise: `to_iso_week_date(1, 1, 1)` is `(1, 1, 1)` and `to_iso_week_date(9999, 12, 31)` is `(9999, 52, 5)`" | DETERMINED |
| `test_out_of_range_dates_raise_value_error` (11 cases) | "Raise `ValueError` when `year` is outside `1..9999`, `month` outside `1..12`, or `day` outside `1..n` for that month of that year — `to_iso_week_date(2023, 2, 29)` raises"; the 1900/2100 February 29 cases are fixed by "divisible by 4, except centuries, which need 400 (1900 is not a leap year, 2000 is)" | DETERMINED |
| `test_returns_a_tuple_of_three_ints` | the signature block `def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]` together with "Return `(week_year, week_number, weekday)`". A `NamedTuple` return would also satisfy this test, so open question 1 stays open | DETERMINED |
| `test_matches_the_standard_library_over_a_multi_year_span` | "Follow the ISO-8601 week date as worded for `date.isocalendar()` (<https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar>)" — normative reference to the exact oracle the test uses | DETERMINED |

## Local choices the standard does not settle, kept explicit

- The ban on delegating: "write the calendar arithmetic out explicitly: no
  `date.isocalendar()`, no `strftime` with `%G`/`%V`/`%u`, no library routine
  that already knows the answer."
- The supported range and the error type: "Supported range is 0001-01-01 through
  9999-12-31. Raise `ValueError` when …".
- The calendar: "Dates are proleptic Gregorian", with the leap rule spelled out
  because the range extends before 1582.

## Open questions, verified still open

1. **Plain tuple vs. tuple subclass.** The terse ticket gives only the signature
   `-> tuple[int, int, int]` and "Return `(week_year, week_number, weekday)`". It
   never says the result must not be a `NamedTuple`. Still open.
2. **Content of the `ValueError`.** The terse ticket says only "Raise
   `ValueError`"; it says nothing about the message or about distinguishing which
   of year, month or day was at fault. Still open.
