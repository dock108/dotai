"""Metrics collection helpers for dashboard analytics."""

from __future__ import annotations

from datetime import datetime, timedelta

from .utils import now_utc
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import Playlist, PlaylistMode, PlaylistQuery


async def get_sports_request_counts(
    session: AsyncSession,
    days: int = 30,
) -> dict[str, int]:
    """Get count of requests by sport for the last N days.
    
    Args:
        session: Database session
        days: Number of days to look back
    
    Returns:
        Dictionary mapping sport name to request count
    """
    cutoff = now_utc() - timedelta(days=days)
    
    stmt = (
        select(PlaylistQuery.sport, func.count(PlaylistQuery.id).label("count"))
        .where(
            PlaylistQuery.created_at >= cutoff,
            PlaylistQuery.sport.isnot(None),
            PlaylistQuery.mode == PlaylistMode.sports_highlight,
        )
        .group_by(PlaylistQuery.sport)
        .order_by(func.count(PlaylistQuery.id).desc())
    )
    
    result = await session.execute(stmt)
    return {row.sport: row.count for row in result}


async def get_average_playlist_duration(
    session: AsyncSession,
    days: int = 30,
) -> float:
    """Get average playlist duration in minutes for the last N days.
    
    Args:
        session: Database session
        days: Number of days to look back
    
    Returns:
        Average duration in minutes
    """
    cutoff = now_utc() - timedelta(days=days)
    
    stmt = (
        select(func.avg(Playlist.total_duration_seconds / 60.0).label("avg_duration"))
        .join(PlaylistQuery)
        .where(
            Playlist.created_at >= cutoff,
            PlaylistQuery.mode == PlaylistMode.sports_highlight,
        )
    )
    
    result = await session.execute(stmt)
    avg = result.scalar()
    return round(avg or 0.0, 1)


async def get_cache_hit_rate(
    session: AsyncSession,
    days: int = 30,
) -> dict[str, Any]:
    """Get cache hit rate statistics for the last N days.
    
    Args:
        session: Database session
        days: Number of days to look back
    
    Returns:
        Dictionary with hit_rate, total_requests, cache_hits, cache_misses
    """
    cutoff = now_utc() - timedelta(days=days)
    
    # Count total unique queries (each represents a potential cache hit)
    total_queries_stmt = (
        select(func.count(func.distinct(PlaylistQuery.normalized_signature)))
        .where(
            PlaylistQuery.created_at >= cutoff,
            PlaylistQuery.mode == PlaylistMode.sports_highlight,
        )
    )
    total_queries_result = await session.execute(total_queries_stmt)
    total_queries = total_queries_result.scalar() or 0
    
    # Count playlists (each represents a cache miss - new playlist created)
    # Cache hits would be when a query exists but we return an existing playlist
    # For simplicity, we'll count playlists created vs queries
    total_playlists_stmt = (
        select(func.count(Playlist.id))
        .join(PlaylistQuery)
        .where(
            Playlist.created_at >= cutoff,
            PlaylistQuery.mode == PlaylistMode.sports_highlight,
        )
    )
    total_playlists_result = await session.execute(total_playlists_stmt)
    total_playlists = total_playlists_result.scalar() or 0
    
    # Estimate: if we have more queries than playlists, some were cache hits
    # This is approximate - in reality we'd need to track cache hits explicitly
    cache_hits = max(0, total_queries - total_playlists)
    cache_misses = total_playlists
    total_requests = total_queries
    
    hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0.0
    
    return {
        "hit_rate": round(hit_rate, 1),
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "period_days": days,
    }


async def export_metrics_csv(
    session: AsyncSession,
    days: int = 30,
) -> str:
    """Export metrics to CSV format for simple dashboard.
    
    Args:
        session: Database session
        days: Number of days to look back
    
    Returns:
        CSV string with metrics
    """
    sports_counts = await get_sports_request_counts(session, days)
    avg_duration = await get_average_playlist_duration(session, days)
    cache_stats = await get_cache_hit_rate(session, days)
    
    lines = [
        "Metric,Value",
        f"Average Playlist Duration (minutes),{avg_duration}",
        f"Cache Hit Rate (%),{cache_stats['hit_rate']}",
        f"Total Requests,{cache_stats['total_requests']}",
        f"Cache Hits,{cache_stats['cache_hits']}",
        f"Cache Misses,{cache_stats['cache_misses']}",
        "",
        "Sport,Request Count",
    ]
    
    for sport, count in sorted(sports_counts.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"{sport},{count}")
    
    return "\n".join(lines)

