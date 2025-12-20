from __future__ import annotations

"""
Caching layer abstraction (Redis-backed preferred; in-memory fallback).
"""

import asyncio
from typing import Any, Optional

try:
    import aioredis  # type: ignore
except ImportError:  # pragma: no cover
    aioredis = None


class Cache:
    def __init__(self, url: str | None = None):
        self.url = url
        self._redis = None
        self._memory: dict[str, Any] = {}

    async def connect(self):
        if aioredis and self.url:
            self._redis = await aioredis.from_url(self.url, encoding="utf-8", decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        if self._redis:
            return await self._redis.get(key)
        return self._memory.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self._redis:
            await self._redis.set(key, value, ex=ttl)
        else:
            self._memory[key] = value
            if ttl:
                asyncio.create_task(self._expire(key, ttl))

    async def _expire(self, key: str, ttl: int):
        await asyncio.sleep(ttl)
        self._memory.pop(key, None)





