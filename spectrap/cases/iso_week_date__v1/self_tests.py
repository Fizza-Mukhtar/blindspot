import pytest

import impl


def test_worked_example_2009_12_31():
    assert impl.to_iso_week_date(2009, 12, 31) == (2009, 53, 4)


def test_2021_01_01_is_week_53_of_2020():
    assert impl.to_iso_week_date(2021, 1, 1) == (2020, 53, 5)


def test_2019_12_30_is_week_1_of_2020():
    assert impl.to_iso_week_date(2019, 12, 30) == (2020, 1, 1)


def test_min_extreme_date():
    assert impl.to_iso_week_date(1, 1, 1) == (1, 1, 1)


def test_max_extreme_date():
    assert impl.to_iso_week_date(9999, 12, 31) == (9999, 52, 5)


def test_leap_day_2024_is_valid():
    assert impl.to_iso_week_date(2024, 2, 29) == (2024, 9, 4)


def test_non_leap_year_feb_29_raises():
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 2, 29)


def test_century_non_leap_year_feb_29_raises():
    # 1900 is divisible by 4 but is a century not divisible by 400 -> not leap
    with pytest.raises(ValueError):
        impl.to_iso_week_date(1900, 2, 29)


def test_century_leap_year_feb_29_is_valid():
    # 2000 is divisible by 400 -> leap
    result = impl.to_iso_week_date(2000, 2, 29)
    assert result[2] == 2  # 2000-02-29 is a Tuesday


@pytest.mark.parametrize("year", [0, -1, 10000, 20000])
def test_year_out_of_range_raises(year):
    with pytest.raises(ValueError):
        impl.to_iso_week_date(year, 6, 15)


@pytest.mark.parametrize("month", [0, -1, 13, 100])
def test_month_out_of_range_raises(month):
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, month, 15)


@pytest.mark.parametrize("day", [0, -1, 32])
def test_day_out_of_range_raises(day):
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 1, day)


def test_day_31_invalid_for_30_day_month():
    # April has 30 days
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 4, 31)


def test_weekday_sequence_across_a_full_week():
    # 2023-01-02 is a Monday; check the full Mon..Sun sequence of weekdays
    expected_weekdays = [1, 2, 3, 4, 5, 6, 7]
    days = [2, 3, 4, 5, 6, 7, 8]
    results = [impl.to_iso_week_date(2023, 1, d)[2] for d in days]
    assert results == expected_weekdays


def test_2020_has_53_weeks():
    # 2020-12-31 is a Thursday, so it belongs to week 53 of 2020
    assert impl.to_iso_week_date(2020, 12, 31) == (2020, 53, 4)


def test_2021_has_only_52_weeks():
    # 2022-01-02 is a Sunday and closes out week 52 of 2021
    assert impl.to_iso_week_date(2022, 1, 2) == (2021, 52, 7)


def test_week_number_never_zero_and_within_bounds():
    for month in range(1, 13):
        for day in (1, 15):
            _, week_number, _ = impl.to_iso_week_date(2023, month, day)
            assert 1 <= week_number <= 53


def test_first_thursday_of_year_is_always_week_1():
    # 4 January always falls in week 1 of its own calendar year by definition
    for year in (2018, 2019, 2020, 2021, 2022, 2023):
        week_year, week_number, _ = impl.to_iso_week_date(year, 1, 4)
        assert (week_year, week_number) == (year, 1)


def test_return_type_is_tuple_of_three_ints():
    result = impl.to_iso_week_date(2023, 6, 15)
    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(isinstance(x, int) for x in result)
