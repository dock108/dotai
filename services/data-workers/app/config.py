"""Configuration for data workers."""

import os
from typing import Optional


class Settings:
    """Application settings."""

    def __init__(self):
        # Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Celery
        self.celery_broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        self.celery_result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

        # YouTube API (for YouTube cache worker)
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")

        # Worker settings
        self.worker_log_level = os.getenv("WORKER_LOG_LEVEL", "INFO")
        self.worker_concurrency = int(os.getenv("WORKER_CONCURRENCY", "4"))


settings = Settings()

