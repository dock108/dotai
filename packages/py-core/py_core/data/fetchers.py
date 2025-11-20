"""Placeholder data fetch interfaces for each theory domain."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

from ..schemas.theory import Domain
from .cache import CacheKey, ContextCache


@dataclass(slots=True)
class ContextResult:
    """Common shape returned by data fetchers."""

    highlights: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    data_source_name: str | None = field(default=None)  # Human-readable data source name
    cache_status: str = field(default="fresh")  # 'cached' or 'fresh'
    data_source_details: str | None = field(default=None)  # Additional details about the data source


# Global cache instance (can be replaced with DB-backed cache in production)
_global_cache: ContextCache | None = None


def _get_cache() -> ContextCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = ContextCache()
    return _global_cache


def _default_context(domain: Domain, query: str, limit: int) -> ContextResult:
    timestamp = datetime.utcnow().isoformat()
    return ContextResult(
        highlights=[f"[{domain}] Context stub for '{query}' ({limit} items) at {timestamp}"],
        sources=[f"{domain.value}-knowledge-base"],
        limitations=["Fetching layer not implemented; returning placeholder summary."],
    )


def fetch_youtube_context(
    query: str, limit: int = 5, freshness: str = "7d", cache: ContextCache | None = None
) -> ContextResult:
    """Fetch YouTube context with caching.

    Cache rules:
    - Check for similar queries cached < 7 days old
    - If found, return cached results (client can rescore)
    - Otherwise hit API, store new cache entry
    """
    cache = cache or _get_cache()
    cache_key = CacheKey(context_type="youtube", query=query, filters={"limit": limit, "freshness": freshness})

    # Check cache first
    cached = cache.get(cache_key)
    if cached:
        payload = cached.payload
        return ContextResult(
            highlights=payload.get("highlights", []),
            sources=payload.get("sources", []),
            limitations=payload.get("limitations", []) + ["Loaded from cache"],
            data_source_name="YouTube search",
            cache_status="cached",
            data_source_details=f"Query: {query}, filters: {freshness}, limit: {limit}",
        )

    # Check for similar query (for YouTube similarity matching)
    if cache.is_similar_query_cached("youtube", query, max_age_days=7):
        # Return placeholder indicating similarity match found
        result = _default_context(Domain.playlist, f"{query} (similar cached)", limit)
        result.limitations.append("Similar query found in cache; consider rescoring cached results")
        result.data_source_name = "YouTube search"
        result.cache_status = "cached"
        result.data_source_details = f"Similar query cached, original: {query}"
        return result

    # No cache hit - would hit API here
    result = _default_context(Domain.playlist, f"{query} (freshness={freshness})", limit)
    result.data_source_name = "YouTube search"
    result.cache_status = "fresh"
    result.data_source_details = f"Query: {query}, filters: {freshness}, limit: {limit}"

    # Store in cache
    cache.set(
        cache_key,
        {
            "highlights": result.highlights,
            "sources": result.sources,
            "limitations": result.limitations,
            "query": query,
        },
    )

    return result


def fetch_odds_context(
    query: str, limit: int = 10, freshness: str = "1d", event_date: datetime | None = None, cache: ContextCache | None = None
) -> ContextResult:
    """Fetch odds context with time-based caching.

    Cache rules:
    - If event > 30 days old: once cached, never refetch
    - Future/recent events: TTL based on time-to-event
    """
    cache = cache or _get_cache()
    cache_key = CacheKey(context_type="odds", query=query, filters={"limit": limit, "freshness": freshness})

    cached = cache.get(cache_key)
    if cached:
        payload = cached.payload
        return ContextResult(
            highlights=payload.get("highlights", []),
            sources=payload.get("sources", []),
            limitations=payload.get("limitations", []) + ["Loaded from cache"],
            data_source_name="Historical odds + results",
            cache_status="cached",
            data_source_details="Play-by-play for 2023-2024 NFL regular season" if "NFL" in query else None,
        )

    result = _default_context(Domain.bets, f"{query} (freshness={freshness})", limit)
    result.data_source_name = "Historical odds + results"
    result.cache_status = "fresh"
    result.data_source_details = "Play-by-play data with closing line value"
    cache.set(cache_key, {"highlights": result.highlights, "sources": result.sources, "limitations": result.limitations}, event_date)
    return result


def fetch_crypto_context(
    query: str, limit: int = 10, freshness: str = "1d", cache: ContextCache | None = None
) -> ContextResult:
    """Fetch crypto context with intraday caching (5-15 min TTL)."""
    cache = cache or _get_cache()
    cache_key = CacheKey(context_type="crypto_price", query=query, filters={"limit": limit, "freshness": freshness})

    cached = cache.get(cache_key)
    if cached:
        payload = cached.payload
        return ContextResult(
            highlights=payload.get("highlights", []),
            sources=payload.get("sources", []),
            limitations=payload.get("limitations", []) + ["Loaded from cache"],
            data_source_name="BTC vs ETH dominance 2017-2025 (daily)",
            cache_status="cached",
            data_source_details="Historical price data with liquidity proxies",
        )

    result = _default_context(Domain.crypto, f"{query} (freshness={freshness})", limit)
    result.data_source_name = "BTC vs ETH dominance 2017-2025 (daily)"
    result.cache_status = "fresh"
    result.data_source_details = "Historical price data with liquidity proxies"
    cache.set(cache_key, {"highlights": result.highlights, "sources": result.sources, "limitations": result.limitations})
    return result


def fetch_stock_context(
    query: str, limit: int = 10, freshness: str = "7d", cache: ContextCache | None = None
) -> ContextResult:
    """Fetch stock context with intraday caching (5-15 min TTL for intraday, long-term for historical)."""
    cache = cache or _get_cache()
    cache_key = CacheKey(context_type="stock_price", query=query, filters={"limit": limit, "freshness": freshness})

    cached = cache.get(cache_key)
    if cached:
        payload = cached.payload
        return ContextResult(
            highlights=payload.get("highlights", []),
            sources=payload.get("sources", []),
            limitations=payload.get("limitations", []) + ["Loaded from cache"],
            data_source_name="Stock fundamentals + price history",
            cache_status="cached",
            data_source_details="Revenue growth, margin compression, volume patterns",
        )

    result = _default_context(Domain.stocks, f"{query} (freshness={freshness})", limit)
    result.data_source_name = "Stock fundamentals + price history"
    result.cache_status = "fresh"
    result.data_source_details = "Revenue growth, margin compression, volume patterns"
    cache.set(cache_key, {"highlights": result.highlights, "sources": result.sources, "limitations": result.limitations})
    return result


def fetch_conspiracy_context(
    query: str, limit: int = 5, sources: Sequence[str] | None = None, cache: ContextCache | None = None
) -> ContextResult:
    """Fetch conspiracy context (no special caching rules yet)."""
    sources_list = list(sources) if sources else ["wikidata", "fact-check-db"]
    result = _default_context(Domain.conspiracies, query, limit)
    result.sources = sources_list
    result.data_source_name = "Wikipedia + Fact-check databases"
    result.cache_status = "cached"
    result.data_source_details = "Mainstream encyclopedia entries and verified fact-check sources (no fringe sources)"
    return result

