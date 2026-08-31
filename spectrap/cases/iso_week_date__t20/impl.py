from datetime import date, timedelta

def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert calendar date to ISO-8601 week date.
    
    Returns (week_year, week_number, weekday) following ISO-8601 rules.
    """
    # Validate year
    if not (1 <= year <= 9999):
        raise ValueError("year must be in 1..9999")
    
    # Validate month
    if not (1 <= month <= 12):
        raise ValueError("month must be in 1..12")
    
    # Create date object (validates day automatically)
    d = date(year, month, day)
    
    # Get the weekday (0=Monday, 6=Sunday in Python)
    weekday_0based = d.weekday()
    weekday_iso = weekday_0based + 1  # 1=Monday, 7=Sunday
    
    # Find the Thursday of the week containing this date
    days_to_thursday = 3 - weekday_0based
    thursday = d + timedelta(days=days_to_thursday)
    
    # The Thursday's year is the week_year
    week_year = thursday.year
    
    # Find the Monday of week 1 of week_year
    jan4 = date(week_year, 1, 4)
    jan4_weekday = jan4.weekday()
    monday_of_week1 = jan4 - timedelta(days=jan4_weekday)
    
    # Find the Monday of the week containing this date
    monday = d - timedelta(days=weekday_0based)
    
    # Count weeks from monday_of_week1 to monday
    days_diff = (monday - monday_of_week1).days
    week_number = days_diff // 7 + 1
    
    return (week_year, week_number, weekday_iso)
