from datetime import date, timedelta


def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a calendar date to an ISO-8601 week date.
    
    Args:
        year: Year (1-9999)
        month: Month (1-12)
        day: Day of month
    
    Returns:
        (week_year, week_number, weekday) - ISO-8601 week date components
        where week_year is 1-9999, week_number is 1-53, and weekday is 1-7
    
    Raises:
        ValueError: If the date is invalid or out of range
    """
    # Validate year and month
    if not (1 <= year <= 9999):
        raise ValueError("year is out of range")
    if not (1 <= month <= 12):
        raise ValueError("month is out of range")
    
    # Validate day by attempting to create a date object
    try:
        d = date(year, month, day)
    except ValueError:
        raise ValueError("day is out of range for the given month and year")
    
    # Get day of week (0=Monday, 6=Sunday)
    weekday = d.weekday()
    iso_weekday = weekday + 1  # Convert to ISO format (1=Monday, 7=Sunday)
    
    # Find the Thursday of this week
    days_to_thursday = 3 - weekday
    thursday = d + timedelta(days=days_to_thursday)
    
    # The year of the Thursday is the ISO week year
    iso_year = thursday.year
    
    # Find week number using January 4th of the ISO week year
    jan4 = date(iso_year, 1, 4)
    jan4_weekday = jan4.weekday()
    days_to_jan4_thursday = 3 - jan4_weekday
    week1_thursday = jan4 + timedelta(days=days_to_jan4_thursday)
    
    # Calculate week number
    days_since_week1 = (thursday - week1_thursday).days
    week_number = days_since_week1 // 7 + 1
    
    return (iso_year, week_number, iso_weekday)
