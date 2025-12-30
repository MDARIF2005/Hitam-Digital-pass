from datetime import datetime

def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """Format a datetime object for display."""
    if isinstance(value, datetime):
        return value.strftime(format)
    return value
