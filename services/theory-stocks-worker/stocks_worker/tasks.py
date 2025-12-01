"""Celery tasks for triggering stocks ingestion runs."""

from __future__ import annotations

from celery import Celery, shared_task

from .config import settings
from .logging import logger
from .services import StocksIngestionConfig, manager


app = Celery(
    "theory-stocks-worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["stocks_worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_default_queue="stocks-worker",
)
app.conf.task_routes = {
    "run_stocks_ingestion_job": {"queue": "stocks-worker", "routing_key": "stocks-worker"},
}


@shared_task(name="run_stocks_ingestion_job")
def run_stocks_ingestion_job(run_id: int, config_payload: dict) -> dict:
    logger.info("stocks_ingestion_job_started", run_id=run_id)
    config = StocksIngestionConfig(**config_payload)
    result = manager.run(run_id, config)
    logger.info("stocks_ingestion_job_completed", run_id=run_id, result=result)
    return result



