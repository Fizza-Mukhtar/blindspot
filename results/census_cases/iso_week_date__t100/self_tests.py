import impl
import pytest


# Normal cases - weekday values

def test_monday_is_weekday_1():
    """Test that Monday is weekday 1."""
    # 2023-06-12 is a Monday
    _, _, weekday = impl.to_iso_week_date(2023, 6, 12)
    assert weekday == 1


def test_sunday_is_weekday_7():
    """Test that Sunday is weekday 7."""
    # 2023-06-18 is a Sunday
    _, _, weekday = impl.to_iso_week_date(2023, 6, 18)
    assert weekday == 7


def test_thursday_weekday():
    """Test that Thursday is weekday 4."""
    # 2023-06-15 is a Thursday
    _, _, weekday = impl.to_iso_week_date(2023, 6, 15)
    assert weekday == 4


# Edge cases from the ticket

def test_early_january_in_previous_year_week_53():
    """2021-01-01 should be (2020, 53, 5) - late Dec/early Jan year boundary."""
    week_year, week_number, weekday = impl.to_iso_week_date(2021, 1, 1)
    assert (week_year, week_number, weekday) == (2020, 53, 5)


def test_late_december_in_next_year_week_1():
    """2019-12-30 should be (2020, 1, 1) - late Dec in next year's week 1."""
    week_year, week_number, weekday = impl.to_iso_week_date(2019, 12, 30)
    assert (week_year, week_number, weekday) == (2020, 1, 1)


# Leap year handling

def test_leap_year_feb29():
    """Test Feb 29 in leap year 2024 doesn't raise."""
    week_year, week_number, weekday = impl.to_iso_week_date(2024, 2, 29)
    assert 1 <= week_year <= 9999
    assert 1 <= week_number <= 53
    assert 1 <= weekday <= 7


def test_non_leap_year_feb28():
    """Test Feb 28 in non-leap year works."""
    week_year, week_number, weekday = impl.to_iso_week_date(2023, 2, 28)
    assert 1 <= week_year <= 9999
    assert 1 <= week_number <= 53
    assert 1 <= weekday <= 7


# Extreme dates

def test_earliest_date():
    """Test earliest supported date: 0001-01-01."""
    week_year, week_number, weekday = impl.to_iso_week_date(1, 1, 1)
    assert (week_year, week_number, weekday) == (1, 1, 1)


def test_latest_date():
    """Test latest supported date: 9999-12-31."""
    week_year, week_number, weekday = impl.to_iso_week_date(9999, 12, 31)
    assert week_year == 9999
    assert 1 <= week_number <= 53
    assert 1 <= weekday <= 7


# Error cases - year validation

def test_year_too_low():
    """Test year < 1 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(0, 1, 1)


def test_year_too_high():
    """Test year > 9999 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(10000, 1, 1)


# Error cases - month validation

def test_month_too_low():
    """Test month < 1 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 0, 1)


def test_month_too_high():
    """Test month > 12 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 13, 1)


# Error cases - day validation

def test_day_too_low():
    """Test day < 1 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 6, 0)


def test_day_too_high():
    """Test day > max for month raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 6, 31)


def test_feb29_non_leap_year():
    """Test Feb 29 in non-leap year raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 2, 29)


# Correctness checks

def test_january_4_always_in_week_1():
    """Test that January 4 is always in week 1 of its year."""
    for year in [1, 100, 2000, 2023, 9999]:
        _, week_number, _ = impl.to_iso_week_date(year, 1, 4)
        assert week_number == 1


def test_week_number_in_valid_range():
    """Test that week numbers are always 1-53."""
    test_dates = [
        (2020, 1, 1),
        (2020, 12, 31),
        (2021, 1, 1),
        (2021, 12, 31),
        (2024, 2, 29),
    ]
    for year, month, day in test_dates:
        _, week_number, _ = impl.to_iso_week_date(year, month, day)
        assert 1 <= week_number <= 53


def test_week_year_by_thursday():
    """Test that week year is determined by the Thursday of the week."""
    # Dec 31, 2020 is a Thursday in the week of 2020
    week_year, _, _ = impl.to_iso_week_date(2020, 12, 31)
    assert week_year == 2020
    
    # Jan 1, 2021 is a Friday in the week with Dec 31, 2020 (Thursday)
    week_year, _, _ = impl.to_iso_week_date(2021, 1, 1)
    assert week_year == 2020
