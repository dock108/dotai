"""YouTube cache worker - pre-fetches popular sports queries."""

from datetime import datetime

import structlog

from app.main import app
from app.services.cache import get_redis_client, write_json_cache

logger = structlog.get_logger()

# Popular sports queries to pre-fetch
POPULAR_QUERIES = [
    "NFL highlights from last night",
    "NBA highlights from today",
    "MLB highlights from today",
    "NHL highlights from last night",
    "NFL Week {week} highlights",
    "NBA {month} highlights",
    "MLB {month} highlights",
    "Sports bloopers from this week",
]


@app.task(name="youtube_cache.pre_fetch_popular")
def pre_fetch_popular_queries():
    """Pre-fetch popular sports queries and cache results in Redis.
    
    This worker runs periodically to populate the cache with common queries,
    reducing API latency for users.
    """
    try:
        redis_client = get_redis_client()
        
        # For now, we'll store placeholder cache entries
        # In a full implementation, this would:
        # 1. Use py-core YouTubeClient to search for videos
        # 2. Store the results in Redis with appropriate TTL
        # 3. Use the same cache key format as the API
        
        cache_key_prefix = "youtube_cache:"
        ttl_seconds = 3600  # 1 hour TTL
        
        for query in POPULAR_QUERIES:
            # Replace placeholders with actual dates
            processed_query = query.replace("{week}", str(datetime.now().isocalendar()[1]))
            processed_query = processed_query.replace("{month}", datetime.now().strftime("%B"))
            
            cache_key = f"{cache_key_prefix}{processed_query}"
            
            # Check if already cached and fresh
            existing = redis_client.get(cache_key)
            if existing:
                logger.info("Query already cached", query=processed_query)
                continue
            
            # Placeholder: In full implementation, would call YouTube API here
            # For now, just log the intent
            logger.info(
                "Pre-fetching query",
                query=processed_query,
                cache_key=cache_key,
            )
            
            # Placeholder cache entry
            placeholder_data = {
                "query": processed_query,
                "cached_at": datetime.utcnow().isoformat(),
                "videos": [],  # Would contain actual video data
                "api_calls": 0,
            }
            
            write_json_cache(redis_client, cache_key, placeholder_data, ttl_seconds)
            
            logger.info(
                "Cached query",
                query=processed_query,
                ttl_seconds=ttl_seconds,
            )
        
        logger.info("Completed pre-fetching popular queries", count=len(POPULAR_QUERIES))
        return {"status": "success", "queries_cached": len(POPULAR_QUERIES)}
    
    except Exception as e:
        logger.error("Error pre-fetching queries", error=str(e), exc_info=True)
        raise


@app.task(name="youtube_cache.refresh_query")
def refresh_query_cache(query: str, ttl_seconds: int = 3600):
    """Refresh cache for a specific query.
    
    Args:
        query: Search query string
        ttl_seconds: Time to live in seconds
    """
    try:
        redis_client = get_redis_client()
        cache_key = f"youtube_cache:{query}"
        
        # Placeholder: In full implementation, would call YouTube API here
        logger.info("Refreshing query cache", query=query, cache_key=cache_key)
        
        placeholder_data = {
            "query": query,
            "cached_at": datetime.utcnow().isoformat(),
            "videos": [],
            "api_calls": 0,
        }
        
        write_json_cache(redis_client, cache_key, placeholder_data, ttl_seconds)
        
        logger.info("Refreshed query cache", query=query, ttl_seconds=ttl_seconds)
        return {"status": "success", "query": query}
    
    except Exception as e:
        logger.error("Error refreshing query cache", query=query, error=str(e), exc_info=True)
        raise

