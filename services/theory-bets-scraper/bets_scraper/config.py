"""
Typed settings for the Theory Bets scraper service.

Uses Pydantic Settings to load configuration from environment variables
with validation and type safety. Settings are loaded from the root .env
file to maintain consistency across all services.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OddsProviderConfig(BaseModel):
    base_url: str = Field(default="https://api.the-odds-api.com/v4")
    api_key: str | None = None
    default_books: list[str] = Field(default_factory=lambda: ["pinnacle", "fanduel"])
    request_timeout_seconds: int = 15


class ScraperConfig(BaseModel):
    sources: list[str] = Field(default_factory=lambda: ["sports_reference"])
    request_timeout_seconds: int = 20
    max_concurrency: int = 4


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Loads from root .env file (../../.env) to maintain consistency
    with other services. All settings are validated by Pydantic.
    """
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="allow"  # Allow extra env vars without validation errors
    )

    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/2", alias="REDIS_URL")
    odds_api_key: str | None = Field(None, alias="ODDS_API_KEY")
    environment: str = Field("development", alias="ENVIRONMENT")
    scraper_config: ScraperConfig = Field(default_factory=ScraperConfig)
    odds_config: OddsProviderConfig = Field(default_factory=OddsProviderConfig)
    theory_engine_app_path: str | None = Field(None, alias="THEORY_ENGINE_APP_PATH")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached settings instance.
    
    Settings are cached to avoid re-parsing environment variables
    on every access. This is safe because environment variables
    don't change during runtime.
    """
    return Settings()


# Global settings instance - import this in other modules
settings = get_settings()
