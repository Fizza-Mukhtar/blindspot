import pytest
import impl


def test_early_january_wraps_to_previous_year_week_53():
    """2021-01-01 is Friday in week 53 of 2020"""
    assert impl.to_iso_week_date(2021, 1, 1) == (2020, 53, 5)


def test_late_december_wraps_to_next_year_week_1():
    """2019-12-30 is Monday in week 1 of 2020"""
    assert impl.to_iso_week_date(2019, 12, 30) == (2020, 1, 1)


def test_leap_day_in_leap_year():
    """2024-02-29 is valid and returns correct week info"""
    assert impl.to_iso_week_date(2024, 2, 29) == (2024, 9, 4)


def test_simple_date_mid_year():
    """Test a date in the middle of the year"""
    result = impl.to_iso_week_date(2023, 3, 15)
    assert result[0] == 2023
    assert 1 <= result[1] <= 53
    assert result[2] == 3  # Wednesday


def test_monday_of_week_1():
    """The first Monday of week 1 in 2023"""
    assert impl.to_iso_week_date(2023, 1, 2) == (2023, 1, 1)


def test_january_4th_always_in_week_1():
    """January 4 is always in week 1 by definition"""
    result = impl.to_iso_week_date(2023, 1, 4)
    assert result[0] == 2023
    assert result[1] == 1


def test_year_with_53_weeks():
    """2020 has 53 ISO weeks"""
    result = impl.to_iso_week_date(2020, 12, 28)
    assert result[0] == 2020
    assert result[1] == 53


def test_year_with_52_weeks():
    """2021 has 52 ISO weeks"""
    result = impl.to_iso_week_date(2021, 12, 27)
    assert result[0] == 2021
    assert result[1] == 52


def test_lowest_boundary_year_1_january_1():
    """Year 1, January 1 is the lowest supported date"""
    assert impl.to_iso_week_date(1, 1, 1) == (1, 1, 1)


def test_highest_boundary_year_9999_december_31():
    """Year 9999, December 31 is the highest supported date"""
    assert impl.to_iso_week_date(9999, 12, 31) == (9999, 52, 5)


def test_all_weekdays_in_a_week():
    """Test all 7 weekdays are correctly numbered 1-7"""
    # 2023-01-02 is Monday, so we can test a full week
    for i in range(7):
        result = impl.to_iso_week_date(2023, 1, 2 + i)
        assert result[2] == i + 1  # 1=Monday through 7=Sunday


def test_invalid_year_zero():
    """Year 0 is outside the supported range"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(0, 1, 1)


def test_invalid_year_10000():
    """Year 10000 is outside the supported range"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(10000, 1, 1)


def test_invalid_month_0():
    """Month 0 is outside the valid range 1-12"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 0, 1)


def test_invalid_month_13():
    """Month 13 is outside the valid range 1-12"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 13, 1)


def test_invalid_day_0():
    """Day 0 is not valid for any month"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 1, 0)


def test_invalid_day_32_in_january():
    """Day 32 exceeds the maximum for January (31 days)"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 1, 32)


def test_february_29_non_leap_year():
    """February 29 in 2023 (non-leap year) is invalid"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 2, 29)


def test_april_31_invalid():
    """April has only 30 days, so April 31 is invalid"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 4, 31)


def test_leap_year_century_1900_not_leap():
    """1900 is not a leap year (century divisible by 100 but not 400)"""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(1900, 2, 29)


def test_leap_year_century_2000_is_leap():
    """2000 is a leap year (century divisible by 400)"""
    result = impl.to_iso_week_date(2000, 2, 29)
    assert result[0] == 2000
    assert 1 <= result[1] <= 53
