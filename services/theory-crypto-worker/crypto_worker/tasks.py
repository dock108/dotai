"""Celery tasks for triggering crypto ingestion runs."""

from __future__ import annotations

from celery import Celery, shared_task

from .config import settings
from .logging import logger
from .services import CryptoIngestionConfig, manager


app = Celery(
    "theory-crypto-worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["crypto_worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_default_queue="crypto-worker",
)
app.conf.task_routes = {
    "run_crypto_ingestion_job": {"queue": "crypto-worker", "routing_key": "crypto-worker"},
}


@shared_task(name="run_crypto_ingestion_job")
def run_crypto_ingestion_job(run_id: int, config_payload: dict) -> dict:
    logger.info("crypto_ingestion_job_started", run_id=run_id)
    config = CryptoIngestionConfig(**config_payload)
    result = manager.run(run_id, config)
    logger.info("crypto_ingestion_job_completed", run_id=run_id, result=result)
    return result



