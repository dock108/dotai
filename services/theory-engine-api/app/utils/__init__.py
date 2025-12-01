"""
Utility modules for theory-engine-api.

Centralized exports for common utility functions used across routers.
This module provides a single import point for date/time utilities,
error handlers, serialization, and other shared functionality.
"""

from .datetime_utils import calculate_date_range, format_date_for_query, now_utc
from .date_range_utils import build_date_range_from_preset, get_default_date_range
from .serialization import (
    flatten_stats_for_response,
    serialize_date,
    serialize_datetime,
    serialize_jsonb_field,
)

__all__ = [
    # Datetime utilities
    "now_utc",
    "format_date_for_query",
    "calculate_date_range",
    # Date range utilities
    "build_date_range_from_preset",
    "get_default_date_range",
    # Serialization utilities
    "serialize_datetime",
    "serialize_date",
    "serialize_jsonb_field",
    "flatten_stats_for_response",
]

