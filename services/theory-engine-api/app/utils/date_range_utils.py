"""
Utilities for building date ranges from presets and defaults.

Provides functions to convert user-friendly date presets (e.g., "last7days")
into structured DateRange objects for API requests. Used primarily by
the highlights and playlist features.
"""

from datetime import datetime, timedelta

from py_core.schemas.highlight_request import DateRange

from .datetime_utils import now_local


def build_date_range_from_preset(
    preset: str,
    custom_start_date: str | None = None,
    custom_end_date: str | None = None,
) -> DateRange | None:
    """Build a DateRange from a preset or custom dates.
    
    Args:
        preset: Date preset ("last2days", "last7days", "last14days", "last30days", "custom", "historical")
        custom_start_date: Custom start date (required for "custom" and "historical")
        custom_end_date: Custom end date (required for "custom" and "historical")
    
    Returns:
        DateRange object or None if invalid
    """
    now = now_local()
    
    if preset == "custom" and custom_start_date and custom_end_date:
        return DateRange(start_date=custom_start_date, end_date=custom_end_date)
    
    if preset == "historical" and custom_start_date and custom_end_date:
        return DateRange(start_date=custom_start_date, end_date=custom_end_date)
    
    if preset == "last2days":
        # Last 2 days: today and yesterday (1 day ago)
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        return DateRange(start_date=start_date, end_date=end_date)
    
    if preset == "last7days":
        # Last 7 days: today through 6 days ago (7 days total including today)
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=6)).strftime("%Y-%m-%d")
        return DateRange(start_date=start_date, end_date=end_date)
    
    if preset == "last14days":
        # Last 14 days: today through 13 days ago (14 days total including today)
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=13)).strftime("%Y-%m-%d")
        return DateRange(start_date=start_date, end_date=end_date)
    
    if preset == "last30days":
        # Last 30 days: today through 29 days ago (30 days total including today)
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=29)).strftime("%Y-%m-%d")
        return DateRange(start_date=start_date, end_date=end_date)
    
    return None


def get_default_date_range() -> DateRange:
    """Get default date range (last 7 days) for recent highlights focus.
    
    Returns:
        DateRange for last 7 days
    """
    now = now_local()
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=6)).strftime("%Y-%m-%d")
    return DateRange(start_date=start_date, end_date=end_date)

