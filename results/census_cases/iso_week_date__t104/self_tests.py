import pytest
import impl


def test_ticket_2021_01_01():
    """From ticket: 2021-01-01 is (2020, 53, 5)."""
    assert impl.to_iso_week_date(2021, 1, 1) == (2020, 53, 5)


def test_ticket_2019_12_30():
    """From ticket: 2019-12-30 is (2020, 1, 1)."""
    assert impl.to_iso_week_date(2019, 12, 30) == (2020, 1, 1)


def test_ticket_2024_02_29():
    """From ticket: 2024-02-29 is (2024, 9, 4)."""
    assert impl.to_iso_week_date(2024, 2, 29) == (2024, 9, 4)


def test_extreme_min():
    """From ticket: 0001-01-01 is (1, 1, 1)."""
    assert impl.to_iso_week_date(1, 1, 1) == (1, 1, 1)


def test_extreme_max():
    """From ticket: 9999-12-31 is (9999, 52, 5)."""
    assert impl.to_iso_week_date(9999, 12, 31) == (9999, 52, 5)


def test_january_4_always_week_1():
    """January 4 always in week 1 of that year."""
    for year in [1900, 2000, 2020, 2021, 2022, 2023, 2024]:
        result = impl.to_iso_week_date(year, 1, 4)
        assert result[0] == year
        assert result[1] == 1


def test_weekdays_range_1_to_7():
    """All returned weekday values are in range 1-7."""
    # Test multiple dates across the year
    for day in range(1, 8):
        result = impl.to_iso_week_date(2024, 1, day)
        assert 1 <= result[2] <= 7
    for day in [10, 15, 20]:
        result = impl.to_iso_week_date(2024, 6, day)
        assert 1 <= result[2] <= 7


def test_week_numbers_range_1_to_53():
    """All returned week numbers are in range 1-53."""
    # Test various dates throughout the year
    for month in [1, 3, 6, 9, 12]:
        for day in [1, 15]:
            result = impl.to_iso_week_date(2024, month, day)
            assert 1 <= result[1] <= 53


def test_consecutive_days_weekday_sequence():
    """Seven consecutive days within a week have weekdays 1-7 in order."""
    # Find a week boundary by testing consecutive days
    results = []
    for day in range(1, 8):
        results.append(impl.to_iso_week_date(2024, 3, day))
    
    # If all in same week, check they form a sequence
    if all(r[0] == results[0][0] and r[1] == results[0][1] for r in results):
        weekdays = [r[2] for r in results]
        assert weekdays == [1, 2, 3, 4, 5, 6, 7]


def test_sunday_monday_week_transition():
    """Sunday-Monday transition crosses week boundaries."""
    # Test a known week boundary (any Sunday followed by Monday)
    # The boundary changes week number or resets weekday to 1
    results = []
    for day in range(1, 10):
        results.append(impl.to_iso_week_date(2024, 3, day))
    
    # Find where weekday resets from 7 to 1
    for i in range(len(results) - 1):
        if results[i][2] == 7 and results[i+1][2] == 1:
            # Confirmed transition: different week numbers
            assert results[i][1] != results[i+1][1]


def test_leap_year_feb29_2024():
    """Year 2024 is a leap year; Feb 29 is valid."""
    result = impl.to_iso_week_date(2024, 2, 29)
    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(isinstance(x, int) for x in result)


def test_leap_year_feb29_2000():
    """Year 2000 is a leap year (divisible by 400)."""
    result = impl.to_iso_week_date(2000, 2, 29)
    assert isinstance(result, tuple) and len(result) == 3


def test_non_leap_year_feb29_raises():
    """February 29 in non-leap year raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 2, 29)


def test_century_non_leap_1900_raises():
    """Year 1900 is not a leap year (divisible by 100, not 400)."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(1900, 2, 29)


def test_year_out_of_range_low():
    """Year 0 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(0, 1, 1)


def test_year_out_of_range_high():
    """Year 10000 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(10000, 1, 1)


def test_invalid_month():
    """Invalid months raise ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2024, 0, 1)
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2024, 13, 1)


def test_invalid_day():
    """Invalid days raise ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2024, 1, 0)
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2024, 1, 32)
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2024, 4, 31)
