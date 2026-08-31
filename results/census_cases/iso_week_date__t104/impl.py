from datetime import date, timedelta


def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a calendar date to ISO-8601 week date.
    
    Returns (week_year, week_number, weekday) where week_year is the year
    the week belongs to, week_number is 1-53, and weekday is 1-7 with
    Monday=1 and Sunday=7.
    """
    # Validate year
    if not (1 <= year <= 9999):
        raise ValueError(f"year {year} is out of range")
    
    # Validate month
    if not (1 <= month <= 12):
        raise ValueError(f"month {month} must be in 1..12")
    
    # Validate day and create the date object
    try:
        d = date(year, month, day)
    except ValueError:
        raise ValueError(f"day {day} is out of range for {year}-{month:02d}")
    
    # Get ISO weekday (1=Monday, 7=Sunday)
    # Python's weekday() returns 0=Monday, 6=Sunday
    iso_weekday = d.weekday() + 1
    
    # Find the Thursday in the same week as the date
    # Thursday is ISO weekday 4
    thursday = d + timedelta(days=4 - iso_weekday)
    
    # The ISO week year is the year of that Thursday
    iso_year = thursday.year
    
    # Find January 4 of the ISO year (always in week 1)
    jan4 = date(iso_year, 1, 4)
    jan4_weekday = jan4.weekday() + 1
    
    # Find the Thursday in the same week as January 4 (this is week 1's Thursday)
    week1_thursday = jan4 + timedelta(days=4 - jan4_weekday)
    
    # Calculate the week number
    # days_diff is the number of days between week 1's Thursday and this week's Thursday
    days_diff = (thursday - week1_thursday).days
    week_number = days_diff // 7 + 1
    
    return (iso_year, week_number, iso_weekday)
