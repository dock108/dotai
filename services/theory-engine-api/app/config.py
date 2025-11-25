"""
Application configuration for theory-engine-api.

Centralizes all configuration values from environment variables with defaults.
All services should import from this module to ensure single source of truth.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        env_file_encoding="utf-8",
        extra="allow",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/dock108",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")
    celery_default_queue: str = Field(default="bets-scraper", alias="CELERY_DEFAULT_QUEUE")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    @property
    def allowed_cors_origins(self) -> list[str]:
        """CORS origins for local development."""
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3003",
            "http://localhost:3004",
            "http://127.0.0.1:3004",
            "http://localhost:3005",
            "http://127.0.0.1:3005",
        ]

    @property
    def celery_broker(self) -> str:
        """Celery broker URL with fallback to REDIS_URL."""
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        """Celery result backend URL with fallback to broker URL."""
        return self.celery_result_backend or self.celery_broker


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()

