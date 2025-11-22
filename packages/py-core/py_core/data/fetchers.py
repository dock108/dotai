"""Placeholder data fetch interfaces for each theory domain."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Sequence

import httpx

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


def _fetch_wikipedia_context(query: str, limit: int = 5) -> dict[str, Any]:
    """Fetch Wikipedia articles related to a query.
    
    Args:
        query: Search query string
        limit: Maximum number of articles to return
        
    Returns:
        Dictionary with title, summary, url, and key_facts
    """
    try:
        headers = {
            "User-Agent": "dock108-conspiracy-evaluator/1.0 (+https://dock108.ai)",
        }
        with httpx.Client(timeout=10.0, headers=headers) as client:
            # Clean up query - remove common words that don't help search
            query_lower = query.lower()
            search_query = (
                query_lower.replace(" claims", "")
                .replace(" theory", "")
                .replace(" hoax", "")
                .replace(" conspiracy", "")
                .strip()
            )
            
            # Try multiple search strategies
            search_queries: list[str] = [query, search_query]
            
            # Add variations for common conspiracy theory patterns
            if "moon landing" in query_lower:
                search_queries.extend(["Apollo Moon landing hoax", "Moon landing conspiracy theories"])
            if "jfk" in query_lower or "kennedy" in query_lower:
                search_queries.extend(
                    [
                        "John F. Kennedy assassination conspiracy theory",
                        "JFK assassination conspiracy theories",
                        "Single-bullet theory",
                        "Magic bullet theory",
                    ]
                )
            if "9/11" in query_lower or "september 11" in query_lower:
                search_queries.extend(["September 11 attacks", "9/11 conspiracy theories"])
            
            # Try each search query
            for search_q in search_queries:
                # First, try direct page lookup
                page_title_encoded = search_q.replace(" ", "_")
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title_encoded}"
                
                try:
                    summary_response = client.get(summary_url)
                    summary_response.raise_for_status()
                    summary_data = summary_response.json()
                    
                    # Success - we found the page directly
                    extract = summary_data.get("extract", "")
                    key_facts = []
                    if extract:
                        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", extract) if s.strip()]
                        key_facts = sentences[:5]  # First 5 sentences as key facts
                    
                    return {
                        "title": summary_data.get("title", query),
                        "summary": summary_data.get("extract", ""),
                        "url": summary_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "key_facts": key_facts,
                    }
                except httpx.HTTPStatusError:
                    # Page not found, continue to search
                    pass
                
                # Try Wikipedia search API
                search_url = "https://en.wikipedia.org/w/api.php"
                search_params = {
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": search_q,
                    "srlimit": limit,
                    "srprop": "snippet|size",
                }
                
                try:
                    search_response = client.get(search_url, params=search_params)
                    search_response.raise_for_status()
                    search_data = search_response.json()
                    
                    search_results = search_data.get("query", {}).get("search", [])
                    if search_results:
                        for result in search_results[: max(limit, 5)]:
                            page_title = result.get("title", "")
                            if not page_title:
                                continue
                            
                            page_title_encoded = page_title.replace(" ", "_")
                            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title_encoded}"
                            try:
                                summary_response = client.get(summary_url)
                                summary_response.raise_for_status()
                                summary_data = summary_response.json()
                            except httpx.HTTPStatusError:
                                continue
                            
                            extract = summary_data.get("extract", "")
                            key_facts = []
                            if extract:
                                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", extract) if s.strip()]
                                key_facts = sentences[:5]  # First 5 sentences as key facts
                            
                            if extract or key_facts:
                                return {
                                    "title": summary_data.get("title", page_title),
                                    "summary": extract,
                                    "url": summary_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                                    "key_facts": key_facts,
                                }
                except httpx.HTTPError:
                    # Search failed, try next query
                    continue
            
            # All searches failed
            return {
                "title": None,
                "summary": None,
                "url": None,
                "key_facts": [],
            }
    except httpx.HTTPError:
        return {
            "title": None,
            "summary": None,
            "url": None,
            "key_facts": [],
        }
    except Exception:
        return {
            "title": None,
            "summary": None,
            "url": None,
            "key_facts": [],
        }


def _fetch_factcheck_context(query: str, limit: int = 5) -> dict[str, Any]:
    """Fetch fact-check results from Google Fact Check Explorer API.
    
    Args:
        query: Search query string
        limit: Maximum number of claims to return
        
    Returns:
        Dictionary with claims, ratings, and sources
    """
    api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY")
    
    if not api_key:
        # Return empty result if no API key
        return {
            "claims": [],
            "ratings": [],
            "sources": [],
        }
    
    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "query": query,
            "key": api_key,
            "pageSize": limit,
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            claims = []
            ratings = []
            sources = []
            
            for claim in data.get("claims", []):
                text = claim.get("text", "")
                claimant = claim.get("claimant", "")
                claim_date = claim.get("claimDate", "")
                
                # Extract rating
                claim_review = claim.get("claimReview", [])
                if claim_review:
                    review = claim_review[0]
                    rating = review.get("textualRating", "Unknown")
                    publisher = review.get("publisher", {}).get("name", "Unknown")
                    review_url = review.get("url", "")
                    
                    claims.append({
                        "text": text,
                        "claimant": claimant,
                        "date": claim_date,
                        "rating": rating,
                        "publisher": publisher,
                        "url": review_url,
                    })
                    ratings.append(rating)
                    sources.append(f"{publisher}: {text[:100]}...")
            
            return {
                "claims": claims,
                "ratings": ratings,
                "sources": sources,
            }
    except httpx.HTTPError:
        # Return empty result on HTTP errors
        return {
            "claims": [],
            "ratings": [],
            "sources": [],
        }
    except Exception:
        # Return empty result on any other errors
        return {
            "claims": [],
            "ratings": [],
            "sources": [],
        }


def fetch_conspiracy_context(
    query: str, limit: int = 5, sources: Sequence[str] | None = None, cache: ContextCache | None = None
) -> ContextResult:
    """Fetch conspiracy context from Wikipedia and fact-check sources with caching.
    
    Cache rules:
    - Check for similar queries cached < 30 days old
    - If found, return cached results
    - Otherwise hit APIs, store new cache entry
    """
    cache = cache or _get_cache()
    sources_list = list(sources) if sources else ["wikipedia", "fact-check-db"]
    cache_key = CacheKey(
        context_type="conspiracy",
        query=query,
        filters={"limit": limit, "sources": sources_list},
    )
    
    # Check cache first
    cached = cache.get(cache_key)
    if cached:
        payload = cached.payload
        return ContextResult(
            highlights=payload.get("highlights", []),
            sources=payload.get("sources", []),
            limitations=payload.get("limitations", []) + ["Loaded from cache"],
            data_source_name="Wikipedia + Fact-check databases",
            cache_status="cached",
            data_source_details=payload.get("data_source_details"),
        )
    
    # Fetch from APIs
    highlights: list[str] = []
    source_names: list[str] = []
    limitations: list[str] = []
    
    # Fetch Wikipedia context
    wikipedia_data = _fetch_wikipedia_context(query, limit)
    if wikipedia_data.get("title"):
        highlights.append(f"Wikipedia: {wikipedia_data['summary'][:200]}...")
        source_names.append(f"Wikipedia: {wikipedia_data['title']}")
    else:
        limitations.append("Wikipedia API returned no results for this query.")
    
    # Fetch fact-check context
    factcheck_data = _fetch_factcheck_context(query, limit)
    if factcheck_data.get("claims"):
        for claim in factcheck_data["claims"][:3]:  # Top 3 claims
            highlights.append(f"Fact-check ({claim['rating']}): {claim['text'][:150]}...")
            source_names.append(f"{claim['publisher']}: {claim['text'][:50]}...")
    else:
        if not os.getenv("GOOGLE_FACTCHECK_API_KEY"):
            limitations.append("Google Fact Check API key not configured. Fact-check results unavailable.")
        else:
            limitations.append("Fact-check API returned no results for this query.")
    
    # Build data source details
    details_parts = []
    if wikipedia_data.get("title"):
        details_parts.append(f"Wikipedia article: {wikipedia_data['title']}")
    if factcheck_data.get("claims"):
        details_parts.append(f"{len(factcheck_data['claims'])} fact-check claims found")
    data_source_details = "; ".join(details_parts) if details_parts else "Limited results available"
    
    result = ContextResult(
        highlights=highlights if highlights else [f"No context found for '{query}'"],
        sources=source_names if source_names else ["No sources found"],
        limitations=limitations,
        data_source_name="Wikipedia + Fact-check databases",
        cache_status="fresh",
        data_source_details=data_source_details,
    )
    
    # Store in cache
    cache.set(
        cache_key,
        {
            "highlights": result.highlights,
            "sources": result.sources,
            "limitations": result.limitations,
            "data_source_details": result.data_source_details,
            "query": query,
            "wikipedia_data": wikipedia_data,
            "factcheck_data": factcheck_data,
        },
    )
    
    return result

