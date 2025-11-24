"""Celery client used for scheduling background jobs from the API."""

from __future__ import annotations

import os
from functools import lru_cache

from celery import Celery


@lru_cache(maxsize=1)
def get_celery_app() -> Celery:
    broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/2"))
    backend_url = os.getenv("CELERY_RESULT_BACKEND", broker_url)
    app = Celery("theory-engine-api", broker=broker_url, backend=backend_url)
    app.conf.task_default_queue = os.getenv("CELERY_DEFAULT_QUEUE", "bets-scraper")
    return app


