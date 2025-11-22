"""Redis caching helpers shared across workers."""

from __future__ import annotations

import json
from typing import Any

import redis
import structlog

from app.config import settings

logger = structlog.get_logger()


def get_redis_client() -> redis.Redis:
    """Return a Redis client configured for the current environment."""
    return redis.from_url(settings.redis_url, decode_responses=True)


def write_json_cache(client: redis.Redis, cache_key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    """Write JSON payload to Redis with TTL."""
    client.setex(cache_key, ttl_seconds, json.dumps(payload))
    logger.debug("Cache write", cache_key=cache_key, ttl_seconds=ttl_seconds)


