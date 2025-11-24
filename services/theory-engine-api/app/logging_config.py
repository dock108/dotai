"""
Structured logging configuration for theory-engine-api.

Uses structlog to provide JSON-formatted logs with consistent structure
across all services. This enables better log aggregation and analysis
in production environments.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging() -> None:
    """
    Configure structured logging with structlog.
    
    Sets up JSON output with:
    - ISO timestamp formatting
    - Log level inclusion
    - Stack trace rendering for exceptions
    - Context variable merging (for request tracking)
    - Unicode decoding for safe JSON serialization
    
    Logs are output as JSON to stdout, making them easy to parse
    by log aggregation systems (e.g., ELK, Datadog, CloudWatch).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Merge request context
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 timestamps
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,  # Format exceptions
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),  # JSON output
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__ to identify the module)
    
    Returns:
        Configured structlog logger with JSON output
    
    Usage:
        logger = get_logger(__name__)
        logger.info("event", key="value")  # Outputs JSON
    """
    return structlog.get_logger(name)


