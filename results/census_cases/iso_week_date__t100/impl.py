from datetime import date, timedelta

def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a calendar date to an ISO-8601 week date.
    
    Returns (week_year, week_number, weekday) where weekday is 1-7 (Monday-Sunday).
    """
    # Validate year
    if not (1 <= year <= 9999):
        raise ValueError("year is out of range")
    
    # Validate month
    if not (1 <= month <= 12):
        raise ValueError("month is out of range")
    
    # Check leap year and validate day
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    days_in_month_table = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_leap:
        days_in_month_table[2] = 29
    
    if not (1 <= day <= days_in_month_table[month]):
        raise ValueError("day is out of range")
    
    # Create the date
    d = date(year, month, day)
    
    # Get ISO weekday (1=Monday, 7=Sunday)
    weekday = d.weekday() + 1
    
    # Find Monday of this week
    monday = d - timedelta(days=d.weekday())
    
    # Find Thursday of this week
    thursday = monday + timedelta(days=3)
    
    # Week year is the year of the Thursday
    week_year = thursday.year
    
    # Find the first Thursday of the week year
    # (the Thursday in the week containing January 4)
    jan4 = date(week_year, 1, 4)
    first_monday = jan4 - timedelta(days=jan4.weekday())
    first_thursday = first_monday + timedelta(days=3)
    
    # Calculate week number
    days_since_first = (thursday - first_thursday).days
    week_number = days_since_first // 7 + 1
    
    return (week_year, week_number, weekday)
