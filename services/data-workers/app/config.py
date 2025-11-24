"""
Configuration for data workers service.

Loads settings from environment variables with sensible defaults.
This service runs background Celery workers for:
- YouTube video metadata caching
- Odds API snapshot collection
- Market price data updates
"""

import os
from typing import Optional


class Settings:
    """
    Application settings for data workers.
    
    All settings are loaded from environment variables with defaults
    suitable for local development. Production deployments should
    set these via environment variables.
    """

    def __init__(self):
        # Redis connection URL (used for Celery broker and result backend)
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Celery broker URL (where tasks are queued)
        self.celery_broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        
        # Celery result backend (where task results are stored)
        self.celery_result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

        # YouTube API key (required for YouTube cache worker)
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")

        # Worker settings
        self.worker_log_level = os.getenv("WORKER_LOG_LEVEL", "INFO")
        self.worker_concurrency = int(os.getenv("WORKER_CONCURRENCY", "4"))


# Global settings instance
settings = Settings()

