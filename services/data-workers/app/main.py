"""
Celery app configuration for data workers service.

This module configures the Celery application that runs background tasks
for data collection and caching across dock108 services.
"""

import structlog
from celery import Celery

from app.config import settings

# Configure structured logging with JSON output
# Consistent with other dock108 services for log aggregation
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 timestamps
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),  # JSON output
    ],
    wrapper_class=structlog.make_filtering_bound_logger(settings.worker_log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Create Celery app instance
# This is the main entry point for all background workers
app = Celery(
    "data-workers",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.youtube_cache",  # YouTube video metadata caching
        "app.workers.odds_snapshot",  # Sports odds snapshot collection
        "app.workers.market_prices",  # Market price data updates
    ],
)

# Celery task configuration
app.conf.update(
    task_serializer="json",  # JSON serialization for tasks
    accept_content=["json"],
    result_serializer="json",  # JSON serialization for results
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,  # Track when tasks start
    task_time_limit=300,  # Hard time limit: 5 minutes
    task_soft_time_limit=240,  # Soft time limit: 4 minutes (allows cleanup)
    worker_prefetch_multiplier=1,  # Fair task distribution
    worker_max_tasks_per_child=1000,  # Restart workers after 1000 tasks (memory leak prevention)
)

logger.info("Celery app configured", broker=settings.celery_broker_url)

