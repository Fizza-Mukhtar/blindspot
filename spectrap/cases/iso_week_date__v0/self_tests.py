import pytest

import impl


def test_worked_example_2009_12_31():
    assert impl.to_iso_week_date(2009, 12, 31) == (2009, 53, 4)


def test_2021_01_01_belongs_to_previous_week_year():
    assert impl.to_iso_week_date(2021, 1, 1) == (2020, 53, 5)


def test_2019_12_30_belongs_to_next_week_year():
    assert impl.to_iso_week_date(2019, 12, 30) == (2020, 1, 1)


def test_lower_extreme_0001_01_01():
    assert impl.to_iso_week_date(1, 1, 1) == (1, 1, 1)


def test_upper_extreme_9999_12_31():
    assert impl.to_iso_week_date(9999, 12, 31) == (9999, 52, 5)


def test_leap_day_2024_is_valid():
    assert impl.to_iso_week_date(2024, 2, 29) == (2024, 9, 4)


def test_leap_day_2023_raises_because_not_a_leap_year():
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 2, 29)


def test_century_year_1900_not_leap_feb_29_raises():
    with pytest.raises(ValueError):
        impl.to_iso_week_date(1900, 2, 29)


def test_century_year_2000_is_leap_feb_29_valid():
    week_year, week_number, weekday = impl.to_iso_week_date(2000, 2, 29)
    assert (week_year, week_number, weekday) == (2000, 9, 2)


@pytest.mark.parametrize("year", [0, -1, 10000, 100000])
def test_year_out_of_range_raises(year):
    with pytest.raises(ValueError):
        impl.to_iso_week_date(year, 1, 1)


@pytest.mark.parametrize("month", [0, -1, 13, 100])
def test_month_out_of_range_raises(month):
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, month, 1)


@pytest.mark.parametrize("day", [0, -1, 32])
def test_day_out_of_range_raises(day):
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 1, day)


def test_day_out_of_range_for_short_month_april_31_raises():
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 4, 31)


def test_weekday_values_span_monday_to_sunday_in_order():
    # 2024-01-01 is a Monday; check the full week Mon..Sun maps to 1..7.
    expected_weekdays = [1, 2, 3, 4, 5, 6, 7]
    days = [1, 2, 3, 4, 5, 6, 7]
    results = [impl.to_iso_week_date(2024, 1, d)[2] for d in days]
    assert results == expected_weekdays


def test_same_week_days_share_week_year_and_week_number():
    # 2024-01-01 (Mon) through 2024-01-07 (Sun) are all in the same ISO week.
    results = [impl.to_iso_week_date(2024, 1, d)[:2] for d in range(1, 8)]
    assert all(r == (2024, 1) for r in results)


def test_2020_has_53_weeks():
    # 2020-12-31 is a Thursday, so it's in week 53 of week-year 2020.
    assert impl.to_iso_week_date(2020, 12, 31) == (2020, 53, 4)


def test_2021_has_only_52_weeks():
    # 2021-12-31 is a Friday; its week's Thursday (2021-12-30) keeps it in
    # week-year 2021, and 2021 only has 52 ISO weeks.
    assert impl.to_iso_week_date(2021, 12, 31) == (2021, 52, 5)


def test_week_number_always_within_valid_bounds():
    # Sweep a range of dates across a leap-year boundary and ensure the
    # week number is always between 1 and 53 inclusive.
    for month in range(1, 13):
        for day in (1, 15):
            _, week_number, _ = impl.to_iso_week_date(2020, month, day)
            assert 1 <= week_number <= 53
