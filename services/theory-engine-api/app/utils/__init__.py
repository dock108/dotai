"""
Utility modules for theory-engine-api.

Centralized exports for common utility functions used across routers.
This module provides a single import point for date/time utilities,
error handlers, serialization, and other shared functionality.

Note: date_range_utils is NOT imported here as it depends on py_core.
Import it directly where needed: from .utils.date_range_utils import ...
"""

from .datetime_utils import calculate_date_range, format_date_for_query, now_utc
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
    # Serialization utilities
    "serialize_datetime",
    "serialize_date",
    "serialize_jsonb_field",
    "flatten_stats_for_response",
]

