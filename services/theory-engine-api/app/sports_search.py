"""Sports-focused YouTube search helpers for highlight playlists."""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx


@dataclass
class SportsSearchSpec:
    """Structured specification for sports video search."""

    sport: str  # NFL, NBA, MLB, NHL, NCAAF, NCAAB, PGA, F1, etc.
    league: str | None = None  # Optional league name
    teams: list[str] | None = None  # Optional team names
    date_range: dict[str, Any] | None = None  # {"start": "2024-11-01", "end": "2024-11-18"} or {"date": "2024-11-12"}
    content_types: list[str] | None = None  # ["highlights", "bloopers", "top plays", "full game", "condensed"]
    duration_target_minutes: int = 10  # Target duration for individual videos


@dataclass
class VideoCandidate:
    """Candidate video from YouTube search."""

    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    duration_seconds: int
    published_at: datetime
    view_count: int
    thumbnail_url: str | None = None
    tags: list[str] | None = None


# Official channel IDs for major sports leagues (partial list)
OFFICIAL_CHANNELS: dict[str, list[str]] = {
    "NFL": [
        "UCDVYQ4Zhbm3S2dlz7P1GBDg",  # NFL
        "UCdZ0XJqJNfNv0Ue9kP3QK9Q",  # NFL Network
    ],
    "NBA": [
        "UCWJ2lWNubArHWmf3F7bf1zw",  # NBA
    ],
    "MLB": [
        "UCq0aX0xRZ7gJ7Y8Y1Y1Y1Y1Y",  # MLB (placeholder)
    ],
    "NHL": [
        "UCq0aX0xRZ7gJ7Y8Y1Y1Y1Y1Y",  # NHL (placeholder)
    ],
    "NCAAF": [
        "UCq0aX0xRZ7gJ7Y8Y1Y1Y1Y1Y",  # NCAA (placeholder)
    ],
    "NCAAB": [
        "UCq0aX0xRZ7gJ7Y8Y1Y1Y1Y1Y",  # NCAA (placeholder)
    ],
}

# Major sports network channel IDs (partial list)
MAJOR_NETWORKS = [
    "UCq0aX0xRZ7gJ7Y8Y1Y1Y1Y1Y",  # ESPN (placeholder)
    "UCq0aX0xRZ7gJ7Y8Y1Y1Y1Y1Y",  # Fox Sports (placeholder)
    "UCq0aX0xRZ7gJ7Y8Y1Y1Y1Y1Y",  # CBS Sports (placeholder)
]


def build_search_queries(spec: SportsSearchSpec) -> list[str]:
    """Build YouTube search queries from structured spec.
    
    Uses query templates based on available information:
    - "{team} vs {opponent} highlights {date}"
    - "{league} highlights {date}"
    - "{sport} bloopers {year}"
    - etc.
    
    Args:
        spec: Structured search specification
    
    Returns:
        List of search query strings
    """
    queries: list[str] = []
    sport = spec.sport.upper()
    
    # Format date for queries
    date_str = ""
    if spec.date_range:
        if "date" in spec.date_range:
            date_str = spec.date_range["date"]
        elif "start" in spec.date_range and "end" in spec.date_range:
            # Use start date for single-day queries, range for multi-day
            if spec.date_range["start"] == spec.date_range["end"]:
                date_str = spec.date_range["start"]
            else:
                date_str = f"{spec.date_range['start']} to {spec.date_range['end']}"
    
    # Determine content type keywords
    content_keywords = spec.content_types or ["highlights"]
    
    # Build queries based on available information
    if spec.teams and len(spec.teams) >= 2:
        # Team vs team query
        team1, team2 = spec.teams[0], spec.teams[1]
        for content_type in content_keywords:
            query = f"{team1} vs {team2} {content_type}"
            if date_str:
                query += f" {date_str}"
            queries.append(query)
    
    if spec.league:
        # League-specific query
        for content_type in content_keywords:
            query = f"{spec.league} {content_type}"
            if date_str:
                query += f" {date_str}"
            queries.append(query)
    
    # Sport-level query (fallback)
    for content_type in content_keywords:
        query = f"{sport} {content_type}"
        if date_str:
            query += f" {date_str}"
        queries.append(query)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)
    
    return unique_queries[:5]  # Limit to 5 queries


def get_channel_reputation_score(channel_id: str, sport: str) -> float:
    """Calculate channel reputation score.
    
    Scoring:
    - Official league/team channels: 1.0
    - Major sports networks: 0.8
    - Others: 0.5
    
    Args:
        channel_id: YouTube channel ID
        sport: Sport name (for official channel lookup)
    
    Returns:
        Reputation score (0.0 - 1.0)
    """
    # Check official channels
    official_channels = OFFICIAL_CHANNELS.get(sport.upper(), [])
    if channel_id in official_channels:
        return 1.0
    
    # Check major networks
    if channel_id in MAJOR_NETWORKS:
        return 0.8
    
    # Default score
    return 0.5


def calculate_highlight_score(
    video: VideoCandidate,
    event_date: datetime | None,
    sport: str,
) -> dict[str, float]:
    """Calculate highlight detection and scoring.
    
    Scores:
    - highlight_score: Based on title/description keywords
    - channel_reputation: Official channels > major networks > others
    - view_count_normalized: Normalized view count (0-1)
    - freshness_score: Based on difference between video publish date and event date
    - final_score: Combined score for ranking
    
    Args:
        video: Video candidate
        event_date: Date of the sports event (if known)
        sport: Sport name
    
    Returns:
        Dictionary with scoring breakdown
    """
    # 1. Highlight keyword detection
    highlight_keywords = [
        "highlight",
        "highlights",
        "condensed",
        "recap",
        "top plays",
        "top play",
        "best plays",
        "bloopers",
        "blooper",
        "full game",
        "game recap",
        "game summary",
    ]
    
    text = f"{video.title} {video.description}".lower()
    keyword_matches = sum(1 for keyword in highlight_keywords if keyword in text)
    highlight_score = min(keyword_matches / 3.0, 1.0)  # Normalize to 0-1
    
    # 2. Channel reputation
    channel_reputation = get_channel_reputation_score(video.channel_id, sport)
    
    # 3. View count normalization (log scale)
    # Assume typical highlight videos get 10K-10M views
    if video.view_count > 0:
        log_views = math.log10(video.view_count + 1)
        # Normalize: 4 (10K) = 0.4, 7 (10M) = 1.0
        view_count_normalized = min((log_views - 3) / 4.0, 1.0)
        view_count_normalized = max(view_count_normalized, 0.1)  # Minimum 0.1
    else:
        view_count_normalized = 0.1
    
    # 4. Freshness score
    freshness_score = 1.0
    if event_date:
        days_diff = abs((video.published_at - event_date).days)
        if days_diff == 0:
            freshness_score = 1.0
        elif days_diff <= 1:
            freshness_score = 0.9
        elif days_diff <= 3:
            freshness_score = 0.7
        elif days_diff <= 7:
            freshness_score = 0.5
        elif days_diff <= 30:
            freshness_score = 0.3
        else:
            freshness_score = 0.1
    
    # 5. Combined final score
    # Weighted combination
    final_score = (
        highlight_score * 0.3
        + channel_reputation * 0.3
        + view_count_normalized * 0.2
        + freshness_score * 0.2
    )
    
    return {
        "highlight_score": highlight_score,
        "channel_reputation": channel_reputation,
        "view_count_normalized": view_count_normalized,
        "freshness_score": freshness_score,
        "final_score": final_score,
    }


async def search_youtube_sports(
    spec: SportsSearchSpec,
    api_key: str | None = None,
    max_results: int = 50,
) -> tuple[list[VideoCandidate], int]:
    """Search YouTube for sports videos based on structured spec.
    
    Args:
        spec: Structured search specification
        api_key: YouTube Data API key (or from env)
        max_results: Maximum number of results to return
    
    Returns:
        Tuple of (list of video candidates with scoring, number of YouTube API calls made)
    """
    api_key = api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("YouTube API key required (set YOUTUBE_API_KEY env var)")
    
    # Build search queries
    queries = build_search_queries(spec)
    
    # Determine duration filters based on content type
    duration_filters = get_duration_filters(spec.content_types or ["highlights"])
    
    all_candidates: list[VideoCandidate] = []
    seen_video_ids = set()
    api_call_count = 0  # Track YouTube API calls
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in queries:
            # Search API call
            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": min(50, max_results),
                "order": "relevance",
                "key": api_key,
            }
            
            # Add channel filter if we have official channels
            official_channels = OFFICIAL_CHANNELS.get(spec.sport.upper(), [])
            if official_channels:
                # Prefer official channels but don't restrict
                pass  # Could add channelId filter here if needed
            
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_response = await client.get(search_url, params=search_params)
            search_response.raise_for_status()
            api_call_count += 1  # Count search API call
            search_data = search_response.json()
            
            video_ids = [
                item["id"]["videoId"]
                for item in search_data.get("items", [])
                if "videoId" in item.get("id", {})
            ]
            
            if not video_ids:
                continue
            
            # Get video details
            videos_params = {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
                "key": api_key,
            }
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            videos_response = await client.get(videos_url, params=videos_params)
            videos_response.raise_for_status()
            api_call_count += 1  # Count videos API call
            videos_data = videos_response.json()
            
            # Parse video details
            for item in videos_data.get("items", []):
                video_id = item["id"]
                if video_id in seen_video_ids:
                    continue
                seen_video_ids.add(video_id)
                
                snippet = item.get("snippet", {})
                content_details = item.get("contentDetails", {})
                statistics = item.get("statistics", {})
                
                # Parse duration
                duration_str = content_details.get("duration", "PT0S")
                duration_seconds = parse_iso_duration(duration_str)
                
                # Apply duration filter
                if not matches_duration_filter(duration_seconds, duration_filters):
                    continue
                
                # Parse published date
                published_str = snippet.get("publishedAt", "")
                try:
                    published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    published_at = datetime.utcnow()
                
                # Get event date from spec
                event_date = None
                if spec.date_range:
                    if "date" in spec.date_range:
                        try:
                            event_date = datetime.fromisoformat(spec.date_range["date"])
                        except (ValueError, AttributeError):
                            pass
                    elif "start" in spec.date_range:
                        try:
                            event_date = datetime.fromisoformat(spec.date_range["start"])
                        except (ValueError, AttributeError):
                            pass
                
                candidate = VideoCandidate(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    channel_id=snippet.get("channelId", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    duration_seconds=duration_seconds,
                    published_at=published_at,
                    view_count=int(statistics.get("viewCount", 0)),
                    thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url"),
                    tags=snippet.get("tags", []),
                )
                
                all_candidates.append(candidate)
                
                if len(all_candidates) >= max_results:
                    break
            
            if len(all_candidates) >= max_results:
                break
    
    # Score and sort candidates
    scored_candidates = []
    for candidate in all_candidates:
        scores = calculate_highlight_score(candidate, event_date, spec.sport)
        scored_candidates.append((candidate, scores))
    
    # Sort by final_score descending
    scored_candidates.sort(key=lambda x: x[1]["final_score"], reverse=True)
    
    return [candidate for candidate, _ in scored_candidates[:max_results]], api_call_count


def get_duration_filters(content_types: list[str]) -> dict[str, tuple[int, int | None]]:
    """Get duration filter ranges based on content types.
    
    Args:
        content_types: List of content types (highlights, bloopers, etc.)
    
    Returns:
        Dictionary mapping content type to (min_seconds, max_seconds)
    """
    filters: dict[str, tuple[int, int | None]] = {}
    
    for content_type in content_types:
        content_lower = content_type.lower()
        if "top plays" in content_lower or "bloopers" in content_lower:
            filters[content_type] = (0, 300)  # < 5 minutes
        elif "highlights" in content_lower or "condensed" in content_lower:
            filters[content_type] = (300, 900)  # 5-15 minutes
        elif "full game" in content_lower:
            filters[content_type] = (3600, None)  # > 1 hour
        else:
            filters[content_type] = (60, 1800)  # 1-30 minutes default
    
    return filters


def matches_duration_filter(duration_seconds: int, filters: dict[str, tuple[int, int | None]]) -> bool:
    """Check if duration matches any of the filters.
    
    Args:
        duration_seconds: Video duration in seconds
        filters: Duration filter ranges
    
    Returns:
        True if duration matches any filter
    """
    if not filters:
        return True
    
    for min_sec, max_sec in filters.values():
        if duration_seconds >= min_sec:
            if max_sec is None or duration_seconds <= max_sec:
                return True
    
    return False


def parse_iso_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration string to seconds.
    
    Example: "PT15M33S" -> 933
    
    Args:
        duration_str: ISO 8601 duration string
    
    Returns:
        Duration in seconds
    """
    # Match patterns like PT15M33S, PT1H30M, etc.
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, duration_str)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

