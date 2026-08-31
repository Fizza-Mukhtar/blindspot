import pytest
import impl


class TestToIsoWeekDate:
    """Test suite for to_iso_week_date function."""
    
    # Basic functionality - different weekdays
    def test_monday_mid_year(self):
        """Test a Monday in the middle of the year."""
        result = impl.to_iso_week_date(2023, 1, 2)
        assert result == (2023, 1, 1)
    
    def test_friday_mid_year(self):
        """Test a Friday in the middle of the year."""
        result = impl.to_iso_week_date(2023, 1, 6)
        assert result == (2023, 1, 5)
    
    def test_sunday_mid_year(self):
        """Test a Sunday in the middle of the year."""
        result = impl.to_iso_week_date(2023, 1, 8)
        assert result == (2023, 1, 7)
    
    # Year boundary cases (from spec)
    def test_late_december_2019_rolls_to_2020_week_1(self):
        """Late December 2019 should be week 1 of 2020."""
        result = impl.to_iso_week_date(2019, 12, 30)
        assert result == (2020, 1, 1)
    
    def test_early_january_2021_rolls_to_2020_week_53(self):
        """Early January 2021 should be week 53 of 2020."""
        result = impl.to_iso_week_date(2021, 1, 1)
        assert result == (2020, 53, 5)
    
    def test_year_boundary_2020_2021(self):
        """Test sequence around year boundary 2020/2021."""
        assert impl.to_iso_week_date(2020, 12, 28) == (2020, 53, 1)
        assert impl.to_iso_week_date(2020, 12, 31) == (2020, 53, 4)
        assert impl.to_iso_week_date(2021, 1, 4) == (2021, 1, 1)
    
    # Leap year tests
    def test_leap_year_feb_29(self):
        """Leap years have Feb 29."""
        result_2020 = impl.to_iso_week_date(2020, 2, 29)
        assert result_2020[0] == 2020 and 1 <= result_2020[1] <= 53
        
        result_2000 = impl.to_iso_week_date(2000, 2, 29)
        assert result_2000[0] == 2000 and 1 <= result_2000[1] <= 53
    
    def test_non_leap_year_feb_28(self):
        """Non-leap years end at Feb 28."""
        result = impl.to_iso_week_date(2021, 2, 28)
        assert result[0] == 2021 and 1 <= result[1] <= 53
    
    # Extremes from spec
    def test_extreme_year_1_jan_1(self):
        """Year 1, Jan 1 should be (1, 1, 1)."""
        result = impl.to_iso_week_date(1, 1, 1)
        assert result == (1, 1, 1)
    
    def test_extreme_year_9999_dec_31(self):
        """Year 9999, Dec 31 should be (9999, 52, 5)."""
        result = impl.to_iso_week_date(9999, 12, 31)
        assert result == (9999, 52, 5)
    
    # Error cases - invalid year
    def test_error_year_out_of_range(self):
        """Year must be in range 1-9999."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(0, 1, 1)
        with pytest.raises(ValueError):
            impl.to_iso_week_date(-1, 1, 1)
        with pytest.raises(ValueError):
            impl.to_iso_week_date(10000, 1, 1)
    
    # Error cases - invalid month
    def test_error_month_out_of_range(self):
        """Month must be in range 1-12."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2023, 0, 1)
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2023, 13, 1)
    
    # Error cases - invalid day
    def test_error_day_out_of_range(self):
        """Day must be valid for the month."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2023, 1, 0)
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2023, 1, 32)
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2023, 4, 31)
    
    def test_error_feb_29_invalid(self):
        """Feb 29 is only valid in leap years."""
        with pytest.raises(ValueError):
            impl.to_iso_week_date(2021, 2, 29)
        with pytest.raises(ValueError):
            impl.to_iso_week_date(1900, 2, 29)
    
    # Additional coverage
    def test_middle_of_year(self):
        """Test a date in the middle of the year."""
        result = impl.to_iso_week_date(2023, 7, 15)
        assert result[0] == 2023
        assert 1 <= result[1] <= 53
        assert 1 <= result[2] <= 7
