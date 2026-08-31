import pytest
import impl

class TestToIsoWeekDate:
    """Test suite for to_iso_week_date implementation."""
    
    # Examples directly from the ticket - guaranteed correct
    def test_ticket_example_2021_01_01(self):
        """2021-01-01 is Friday in week 53 of 2020."""
        assert impl.to_iso_week_date(2021, 1, 1) == (2020, 53, 5)
    
    def test_ticket_example_2019_12_30(self):
        """2019-12-30 is Monday in week 1 of 2020."""
        assert impl.to_iso_week_date(2019, 12, 30) == (2020, 1, 1)
    
    def test_ticket_example_year_1_month_1_day_1(self):
        """Year 1, Jan 1 - minimum valid date."""
        assert impl.to_iso_week_date(1, 1, 1) == (1, 1, 1)
    
    def test_ticket_example_year_9999_month_12_day_31(self):
        """Year 9999, Dec 31 - maximum valid date."""
        assert impl.to_iso_week_date(9999, 12, 31) == (9999, 52, 5)
    
    # Leap year edge cases
    def test_leap_year_2020_feb_29_valid(self):
        """2020 is a leap year, Feb 29 should be valid."""
        result = impl.to_iso_week_date(2020, 2, 29)
        assert result[0] == 2020
        assert 1 <= result[1] <= 53
        assert 1 <= result[2] <= 7
    
    def test_leap_year_2024_feb_29_valid(self):
        """2024 is a leap year, Feb 29 should be valid."""
        result = impl.to_iso_week_date(2024, 2, 29)
        assert result[0] == 2024
        assert 1 <= result[1] <= 53
        assert 1 <= result[2] <= 7
    
    def test_leap_year_2000_feb_29_valid(self):
        """2000 is divisible by 400, so it is a leap year."""
        result = impl.to_iso_week_date(2000, 2, 29)
        assert result[0] == 2000
        assert 1 <= result[1] <= 53
        assert 1 <= result[2] <= 7
    
    def test_non_leap_year_2023_feb_29_raises(self):
        """2023 is not a leap year, Feb 29 should raise ValueError."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2023, 2, 29)
    
    def test_non_leap_year_1900_feb_29_raises(self):
        """1900 is divisible by 100 but not 400, not a leap year."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(1900, 2, 29)
    
    def test_non_leap_year_2100_feb_29_raises(self):
        """2100 is divisible by 100 but not 400, not a leap year."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2100, 2, 29)
    
    # Year validation
    def test_year_0_raises(self):
        """Year must be >= 1."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(0, 1, 1)
    
    def test_year_10000_raises(self):
        """Year must be <= 9999."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(10000, 1, 1)
    
    def test_year_negative_raises(self):
        """Negative year should raise ValueError."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(-1, 6, 15)
    
    # Month validation
    def test_month_0_raises(self):
        """Month must be >= 1."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2020, 0, 1)
    
    def test_month_13_raises(self):
        """Month must be <= 12."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2020, 13, 1)
    
    def test_month_negative_raises(self):
        """Negative month should raise ValueError."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2020, -1, 15)
    
    # Day validation
    def test_day_0_raises(self):
        """Day must be >= 1."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2020, 1, 0)
    
    def test_day_32_in_january_raises(self):
        """January has 31 days."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2020, 1, 32)
    
    def test_day_31_in_april_raises(self):
        """April has 30 days."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2020, 4, 31)
    
    def test_day_30_in_february_non_leap_raises(self):
        """February in non-leap year has 28 days."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2023, 2, 30)
    
    # Weekday correctness
    def test_weekday_1_is_monday(self):
        """Verify weekday 1 is used for Monday (2023-01-02 is Monday)."""
        result = impl.to_iso_week_date(2023, 1, 2)
        assert result[2] == 1
    
    def test_weekday_7_is_sunday(self):
        """Verify weekday 7 is used for Sunday (2023-01-01 is Sunday)."""
        result = impl.to_iso_week_date(2023, 1, 1)
        assert result[2] == 7
    
    def test_weekday_4_is_thursday(self):
        """Verify weekday 4 is Thursday (2023-01-05 is Thursday)."""
        result = impl.to_iso_week_date(2023, 1, 5)
        assert result[2] == 4
    
    # Year boundary transitions - early January
    def test_2020_01_01_wednesday_in_week_1_2020(self):
        """2020-01-01 is Wednesday, belongs to week 1 of 2020."""
        result = impl.to_iso_week_date(2020, 1, 1)
        assert result == (2020, 1, 3)
    
    def test_2022_01_03_monday_in_week_1_2022(self):
        """2022-01-03 is Monday, first day of week 1 of 2022."""
        result = impl.to_iso_week_date(2022, 1, 3)
        assert result[0] == 2022
        assert result[1] == 1
        assert result[2] == 1
    
    # Year boundary transitions - late December
    def test_2020_12_31_thursday_in_week_53_2020(self):
        """2020-12-31 is Thursday, belongs to week 53 of 2020."""
        result = impl.to_iso_week_date(2020, 12, 31)
        assert result[0] == 2020
        assert result[1] == 53
        assert result[2] == 4
    
    def test_2024_12_30_monday_in_week_1_2025(self):
        """2024-12-30 is Monday, first day of week 1 of 2025."""
        result = impl.to_iso_week_date(2024, 12, 30)
        assert result[0] == 2025
        assert result[1] == 1
        assert result[2] == 1
    
    # Invariants: week number and weekday always valid
    def test_week_number_always_valid(self):
        """Week number is always between 1 and 53."""
        test_cases = [
            (1, 1, 1),
            (2020, 1, 1),
            (2020, 2, 29),
            (2020, 6, 15),
            (2020, 12, 31),
            (9999, 12, 31),
        ]
        for year, month, day in test_cases:
            week_year, week_num, weekday = impl.to_iso_week_date(year, month, day)
            assert 1 <= week_num <= 53, f"Invalid week {week_num} for {year}-{month:02d}-{day:02d}"
    
    def test_weekday_always_valid(self):
        """Weekday is always between 1 (Monday) and 7 (Sunday)."""
        test_cases = [
            (1, 1, 1),
            (2020, 1, 1),
            (2020, 2, 29),
            (2020, 6, 15),
            (2020, 12, 31),
            (9999, 12, 31),
        ]
        for year, month, day in test_cases:
            week_year, week_num, weekday = impl.to_iso_week_date(year, month, day)
            assert 1 <= weekday <= 7, f"Invalid weekday {weekday} for {year}-{month:02d}-{day:02d}"
    
    # Year with 53 weeks (known: 2020 has 53 weeks)
    def test_2020_has_53_weeks_verified(self):
        """2020 has 53 weeks (ends on Thursday)."""
        result = impl.to_iso_week_date(2020, 12, 31)
        assert result[1] == 53
    
    # Normal mid-year dates
    def test_2023_06_15(self):
        """Mid-year date produces valid results."""
        result = impl.to_iso_week_date(2023, 6, 15)
        week_year, week_num, weekday = result
        assert 1 <= week_year <= 2023
        assert 1 <= week_num <= 53
        assert 1 <= weekday <= 7
