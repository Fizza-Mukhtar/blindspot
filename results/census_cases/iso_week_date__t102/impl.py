from datetime import date, timedelta


def to_iso_week_date(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a calendar date to ISO-8601 week date.
    
    Returns a tuple of (ISO year, ISO week number, ISO weekday).
    ISO weekday is 1 for Monday through 7 for Sunday.
    """
    
    # Create the date, which validates the input
    d = date(year, month, day)
    
    # Get the ISO week day (1=Monday, 7=Sunday)
    weekday = d.isoweekday()
    
    # Find January 4 of this year and the Monday of week 1
    jan4 = date(year, 1, 4)
    jan4_weekday = jan4.isoweekday()
    monday_of_week1 = jan4 - timedelta(days=jan4_weekday - 1)
    
    # Check if our date is before the Monday of week 1 (in previous year's last week)
    if d < monday_of_week1:
        week_year = year - 1
        jan4_prev = date(year - 1, 1, 4)
        jan4_prev_weekday = jan4_prev.isoweekday()
        monday_of_week1_prev = jan4_prev - timedelta(days=jan4_prev_weekday - 1)
        week_number = ((d - monday_of_week1_prev).days // 7) + 1
    else:
        # Check if our date is in the next year's first week (only if year < 9999)
        week_year = year
        week_number = ((d - monday_of_week1).days // 7) + 1
        
        if year < 9999:
            next_year_jan4 = date(year + 1, 1, 4)
            next_year_jan4_weekday = next_year_jan4.isoweekday()
            monday_of_week1_next = next_year_jan4 - timedelta(days=next_year_jan4_weekday - 1)
            
            if d >= monday_of_week1_next:
                week_year = year + 1
                week_number = ((d - monday_of_week1_next).days // 7) + 1
    
    return (week_year, week_number, weekday)
