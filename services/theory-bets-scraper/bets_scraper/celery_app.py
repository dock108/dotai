"""Celery app configuration for bets scraper."""

from __future__ import annotations

from celery import Celery

from .config import settings

celery_config = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "worker_prefetch_multiplier": 1,
    "task_time_limit": 600,
    "task_soft_time_limit": 540,
    "task_default_queue": "bets-scraper",
    "task_routes": {
        "run_scrape_job": {"queue": "bets-scraper"},
    },
}

app = Celery(
    "theory-bets-scraper",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["bets_scraper.jobs.tasks"],
)
app.conf.update(**celery_config)
app.conf.task_routes = {
    "run_scrape_job": {"queue": "bets-scraper", "routing_key": "bets-scraper"},
}


