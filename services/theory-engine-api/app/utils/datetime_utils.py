"""Centralized datetime utilities to avoid scattered imports."""

from datetime import datetime, timedelta, timezone
from typing import Any


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    """Get current local datetime."""
    return datetime.now()


def format_date_for_query(date_range: dict[str, Any] | None) -> str:
    """Format date range for inclusion in YouTube search query.
    
    Formats dates in ways that match how sports media organizations tag videos:
    - "November 2024" for month ranges
    - "Week 9 2024" for week ranges
    - "2024" for year ranges
    - "November 1-15, 2024" for specific date ranges
    
    Args:
        date_range: Date range dict with start/end or single_date
    
    Returns:
        Formatted date string for query, or empty string
    """
    from typing import TYPE_CHECKING
    
    if TYPE_CHECKING:
        from typing import Any
    
    if not date_range:
        return ""
    
    try:
        if "date" in date_range:
            # Single date
            date_str = date_range["date"]
            dt = datetime.fromisoformat(date_str) if isinstance(date_str, str) else date_str
            return dt.strftime("%B %Y")  # "November 2024"
        
        if "start" in date_range and "end" in date_range:
            start_str = date_range["start"]
            end_str = date_range["end"]
            start_dt = datetime.fromisoformat(start_str) if isinstance(start_str, str) else start_str
            end_dt = datetime.fromisoformat(end_str) if isinstance(end_str, str) else end_str
            
            # Same month
            if start_dt.month == end_dt.month and start_dt.year == end_dt.year:
                if start_dt.day == 1 and end_dt.day >= 28:
                    # Full month
                    return start_dt.strftime("%B %Y")  # "November 2024"
                else:
                    # Date range within month
                    return f"{start_dt.strftime('%B %d')}-{end_dt.strftime('%d, %Y')}"  # "November 1-15, 2024"
            
            # Different months, same year
            if start_dt.year == end_dt.year:
                if start_dt.month == 1 and end_dt.month == 12:
                    # Full year
                    return str(start_dt.year)  # "2024"
                else:
                    # Multi-month range
                    return f"{start_dt.strftime('%B')}-{end_dt.strftime('%B %Y')}"  # "November-December 2024"
            
            # Different years
            return f"{start_dt.strftime('%B %Y')}-{end_dt.strftime('%B %Y')}"  # "November 2024-January 2025"
        
        # Fallback: try to extract year
        if "start" in date_range:
            start_str = date_range["start"]
            start_dt = datetime.fromisoformat(start_str) if isinstance(start_str, str) else start_str
            return str(start_dt.year)
        
        return ""
    except (ValueError, AttributeError, KeyError):
        return ""


def calculate_date_range(preset: str, days: int) -> tuple[str, str]:
    """Calculate start and end dates for a preset.
    
    Args:
        preset: Preset name (e.g., "last7days")
        days: Number of days to go back (excluding today)
    
    Returns:
        Tuple of (start_date, end_date) as ISO format strings
    """
    end_date = now_local().strftime("%Y-%m-%d")
    start_date = (now_local() - timedelta(days=days)).strftime("%Y-%m-%d")
    return start_date, end_date

