"""Celery client for scheduling background jobs."""

from __future__ import annotations

from functools import lru_cache

from celery import Celery

from .config import settings


@lru_cache(maxsize=1)
def get_celery_app() -> Celery:
    app = Celery("theory-engine-api", broker=settings.celery_broker, backend=settings.celery_backend)
    app.conf.task_default_queue = settings.celery_default_queue
    app.conf.task_routes = {
        "run_scrape_job": {"queue": "bets-scraper", "routing_key": "bets-scraper"},
        "run_crypto_ingestion_job": {"queue": "crypto-worker", "routing_key": "crypto-worker"},
        "run_stocks_ingestion_job": {"queue": "stocks-worker", "routing_key": "stocks-worker"},
    }
    app.conf.task_always_eager = False
    app.conf.task_eager_propagates = True
    return app


