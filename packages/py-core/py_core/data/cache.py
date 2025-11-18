"""Context caching layer with domain-specific TTL rules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(slots=True)
class CacheKey:
    """Represents a cache lookup key."""

    context_type: str
    query: str
    filters: dict[str, Any] | None = None

    def to_hash(self) -> str:
        """Generate SHA-256 hash of the cache key."""
        key_parts = {
            "type": self.context_type,
            "query": self.query,
            "filters": self.filters or {},
        }
        key_str = json.dumps(key_parts, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()


@dataclass(slots=True)
class CacheEntry:
    """Represents a cached context entry."""

    key_hash: str
    payload: dict[str, Any]
    fetched_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None = None

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if cache entry has expired."""
        if self.expires_at is None:
            return False
        now = now or datetime.utcnow()
        return now >= self.expires_at


class ContextCache:
    """Manages caching rules for different context types."""

    def __init__(self, db_session: Any | None = None):
        """Initialize cache with optional database session for persistence."""
        self.db_session = db_session
        # In-memory fallback cache (for dev/testing)
        self._memory_cache: dict[str, CacheEntry] = {}

    def compute_expires_at(
        self, context_type: str, query: str, filters: dict[str, Any] | None = None, event_date: datetime | None = None
    ) -> datetime | None:
        """Compute expiration time based on context type and rules.

        Rules:
        - YouTube: 7 days
        - Sports (odds/play-by-play): If event > 30 days old, never expire. Otherwise TTL based on time-to-event.
        - Crypto/stocks: 5-15 minutes for intraday, historical stored long-term.
        """
        now = datetime.utcnow()

        if context_type == "youtube":
            return now + timedelta(days=7)

        if context_type in ("odds", "play_by_play"):
            if event_date:
                days_old = (now - event_date).days
                if days_old > 30:
                    # Historical events never expire once cached
                    return None
                # Future/recent events: more aggressive refresh closer to start
                if event_date > now:
                    hours_until = (event_date - now).total_seconds() / 3600
                    if hours_until < 2:
                        return now + timedelta(minutes=15)
                    if hours_until < 24:
                        return now + timedelta(hours=1)
                    return now + timedelta(hours=6)
                # Recent past events: refresh less frequently
                return now + timedelta(hours=12)
            # No event date: default 1 day
            return now + timedelta(days=1)

        if context_type in ("crypto_price", "stock_price"):
            # Intraday: 5-15 minutes
            return now + timedelta(minutes=10)

        # Default: 1 day
        return now + timedelta(days=1)

    def get(self, key: CacheKey) -> CacheEntry | None:
        """Retrieve cache entry by key."""
        key_hash = key.to_hash()

        # Try database first if session available
        if self.db_session:
            # This would query ExternalContextCache table
            # For now, placeholder - actual implementation would use SQLAlchemy
            pass

        # Fallback to memory cache
        entry = self._memory_cache.get(key_hash)
        if entry and not entry.is_expired():
            return entry

        # Expired or not found
        if entry:
            del self._memory_cache[key_hash]
        return None

    def set(self, key: CacheKey, payload: dict[str, Any], event_date: datetime | None = None) -> CacheEntry:
        """Store cache entry with computed expiration."""
        key_hash = key.to_hash()
        now = datetime.utcnow()
        expires_at = self.compute_expires_at(key.context_type, key.query, key.filters, event_date)

        entry = CacheEntry(
            key_hash=key_hash,
            payload=payload,
            fetched_at=now,
            expires_at=expires_at,
            last_used_at=now,
        )

        # Store in database if session available
        if self.db_session:
            # This would insert/update ExternalContextCache table
            # For now, placeholder - actual implementation would use SQLAlchemy
            pass

        # Store in memory cache
        self._memory_cache[key_hash] = entry
        return entry

    def is_similar_query_cached(self, context_type: str, query: str, max_age_days: int = 7) -> bool:
        """Check if a similar enough query is already cached (for YouTube similarity matching).

        This is a simplified check - real implementation would use semantic similarity
        or fuzzy matching on the query text.
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(days=max_age_days)

        for entry in self._memory_cache.values():
            if entry.is_expired(now):
                continue
            if entry.fetched_at < cutoff:
                continue
            # Simple substring match for now - replace with semantic similarity later
            cached_query = entry.payload.get("query", "")
            if query.lower() in cached_query.lower() or cached_query.lower() in query.lower():
                return True

        return False

    def cleanup_expired(self) -> int:
        """Remove expired entries from memory cache. Returns count removed."""
        now = datetime.utcnow()
        expired_keys = [k for k, v in self._memory_cache.items() if v.is_expired(now)]
        for key in expired_keys:
            del self._memory_cache[key]
        return len(expired_keys)

