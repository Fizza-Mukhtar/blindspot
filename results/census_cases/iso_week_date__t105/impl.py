from datetime import date, timedelta

def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a calendar date to ISO-8601 week date format.
    
    Args:
        year: Year in range 1-9999
        month: Month in range 1-12
        day: Day of month
        
    Returns:
        Tuple of (week_year, week_number, weekday) where:
        - week_year is the year containing the ISO week
        - week_number is the ISO week number (1-53)
        - weekday is the ISO weekday (1=Monday, 7=Sunday)
        
    Raises:
        ValueError: If year, month, or day is out of valid range
    """
    # Validate year
    if not (1 <= year <= 9999):
        raise ValueError("year must be in 1..9999")
    
    # Validate month
    if not (1 <= month <= 12):
        raise ValueError("month must be in 1..12")
    
    # Helper function to check leap year (proleptic Gregorian)
    def is_leap_year(y: int) -> bool:
        return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    
    # Days in each month for this year
    days_in_month = [31, 29 if is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    max_day = days_in_month[month - 1]
    
    # Validate day
    if not (1 <= day <= max_day):
        raise ValueError(f"day is out of range for year {year}, month {month}")
    
    # Create date object for the given date
    d = date(year, month, day)
    
    # Get ISO weekday (1=Monday, 7=Sunday)
    iso_weekday = d.isoweekday()
    
    # Find the Thursday of the week containing this date
    # (ISO weekday 4 is Thursday)
    thursday = d - timedelta(days=iso_weekday - 4)
    
    # The year of that Thursday is the week_year
    week_year = thursday.year
    
    # Find the first Thursday of week_year
    # (Week 1 contains January 4, so we find the Thursday of that week)
    jan4 = date(week_year, 1, 4)
    first_thursday = jan4 - timedelta(days=jan4.isoweekday() - 4)
    
    # Calculate week number
    weeks_passed = (thursday - first_thursday).days // 7
    week_number = weeks_passed + 1
    
    return (week_year, week_number, iso_weekday)
