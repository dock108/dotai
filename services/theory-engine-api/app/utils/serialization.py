"""Shared serialization utilities for API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .. import db_models


def serialize_datetime(dt: datetime | None) -> str | None:
    """Serialize datetime to ISO format string.
    
    Args:
        dt: Datetime object or None
        
    Returns:
        ISO format string or None
    """
    return dt.isoformat() if dt else None


def serialize_date(d: datetime | None) -> str | None:
    """Serialize date to ISO format string (date only).
    
    Args:
        d: Datetime object or None
        
    Returns:
        ISO date string (YYYY-MM-DD) or None
    """
    return d.date().isoformat() if d else None


def serialize_jsonb_field(field: dict[str, Any] | None) -> dict[str, Any]:
    """Serialize JSONB field, ensuring it's a dict.
    
    Args:
        field: JSONB field value or None
        
    Returns:
        Dict (empty if None)
    """
    return field if field is not None else {}


def flatten_stats_for_response(stats: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten nested stats dict for API response.
    
    Common pattern: stats are stored as JSONB but need to be flattened
    for API responses (e.g., stats.minutes -> minutes).
    
    Args:
        stats: Stats dict or None
        
    Returns:
        Flattened dict
    """
    if not stats:
        return {}
    
    # If stats is already flat, return as-is
    # Otherwise, extract common fields
    result = {}
    for key in ["minutes", "points", "rebounds", "assists", "yards", "touchdowns"]:
        if key in stats:
            result[key] = stats[key]
    
    # Include raw_stats for full data
    result["raw_stats"] = stats
    return result

