"""Structured logging helpers for the crypto worker."""

from __future__ import annotations

import logging

import structlog


def get_logger(name: str = "crypto_worker") -> structlog.BoundLogger:
    """Return a structured logger with a consistent configuration."""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    return structlog.get_logger(name)


logger = get_logger()


