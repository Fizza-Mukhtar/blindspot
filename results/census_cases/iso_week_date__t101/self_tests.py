import pytest
import impl


def test_basic_return_format():
    """Test that function returns a tuple of 3 integers in valid ranges."""
    result = impl.to_iso_week_date(2023, 6, 15)
    assert isinstance(result, tuple)
    assert len(result) == 3
    year, week, weekday = result
    assert isinstance(year, int)
    assert isinstance(week, int)
    assert isinstance(weekday, int)
    assert 1 <= year <= 9999
    assert 1 <= week <= 53
    assert 1 <= weekday <= 7


def test_year_boundary_forward():
    """Test example from problem: 2019-12-30 crosses into 2020 week 1."""
    result = impl.to_iso_week_date(2019, 12, 30)
    assert result == (2020, 1, 1)


def test_year_boundary_backward():
    """Test example from problem: 2021-01-01 is in 2020 week 53."""
    result = impl.to_iso_week_date(2021, 1, 1)
    assert result == (2020, 53, 5)


def test_minimum_date():
    """Test minimum valid date: year 1, month 1, day 1."""
    result = impl.to_iso_week_date(1, 1, 1)
    assert result == (1, 1, 1)


def test_maximum_date():
    """Test maximum valid date: year 9999, month 12, day 31."""
    result = impl.to_iso_week_date(9999, 12, 31)
    assert result == (9999, 52, 5)


def test_leap_year_feb_29():
    """Test leap year February 29 (2024)."""
    result = impl.to_iso_week_date(2024, 2, 29)
    year, week, weekday = result
    assert 1 <= year <= 9999
    assert 1 <= week <= 53
    assert 1 <= weekday <= 7


def test_century_leap_year():
    """Test century leap year (2000-02-29 is valid; 1900-02-29 would not be)."""
    result = impl.to_iso_week_date(2000, 2, 29)
    year, week, weekday = result
    assert 1 <= year <= 9999
    assert 1 <= week <= 53


def test_january_4_always_week_1():
    """Test that January 4 is always in week 1 of that year."""
    for year in [1, 500, 1000, 2000, 2023, 5000, 9999]:
        result = impl.to_iso_week_date(year, 1, 4)
        assert result[0] == year
        assert result[1] == 1


def test_multiple_valid_dates():
    """Test various dates produce valid output ranges."""
    dates = [
        (2020, 1, 1),
        (2020, 12, 31),
        (2023, 1, 1),
        (2023, 12, 31),
    ]
    for y, m, d in dates:
        result = impl.to_iso_week_date(y, m, d)
        assert 1 <= result[0] <= 9999
        assert 1 <= result[1] <= 53
        assert 1 <= result[2] <= 7


def test_year_below_range():
    """Test that year < 1 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(0, 1, 1)
    with pytest.raises(ValueError):
        impl.to_iso_week_date(-1, 1, 1)


def test_year_above_range():
    """Test that year > 9999 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(10000, 1, 1)
    with pytest.raises(ValueError):
        impl.to_iso_week_date(99999, 6, 15)


def test_month_below_range():
    """Test that month < 1 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 0, 1)


def test_month_above_range():
    """Test that month > 12 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 13, 1)
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 100, 15)


def test_day_zero():
    """Test that day 0 raises ValueError."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 1, 0)


def test_invalid_day_non_leap_year():
    """Test that 2023-02-29 raises ValueError (non-leap year)."""
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 2, 29)


def test_invalid_day_too_large():
    """Test that day values beyond month length raise ValueError."""
    # April has 30 days
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 4, 31)
    # January has 31 days but 32 is invalid
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 1, 32)
    # June has 30 days
    with pytest.raises(ValueError):
        impl.to_iso_week_date(2023, 6, 31)


def test_consecutive_days_same_week():
    """Test that consecutive days maintain week consistency."""
    # Get Monday and Tuesday
    result_mon = impl.to_iso_week_date(2023, 6, 12)
    result_tue = impl.to_iso_week_date(2023, 6, 13)
    
    # If first is not Sunday (weekday 7), they should be in same week
    if result_mon[2] < 7:
        assert result_mon[0] == result_tue[0]
        assert result_mon[1] == result_tue[1]


def test_week_53_exists():
    """Test that 2020 (a 53-week year) works correctly."""
    # 2020-12-28 is Monday of week 53
    result1 = impl.to_iso_week_date(2020, 12, 28)
    assert result1[0] == 2020
    assert result1[1] == 53
    
    # 2020-12-31 is Thursday of week 53
    result2 = impl.to_iso_week_date(2020, 12, 31)
    assert result2[0] == 2020
    assert result2[1] == 53
