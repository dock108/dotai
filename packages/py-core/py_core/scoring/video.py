"""Video scoring utilities for playlist generation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

# Import VideoCandidate from clients module
from ..clients.youtube import VideoCandidate


@dataclass
class VideoScore:
    """Scoring breakdown for a video."""

    keyword_score: float
    channel_reputation: float
    view_count_normalized: float
    freshness_score: float
    length_fit: float
    final_score: float


def calculate_highlight_score(
    video: VideoCandidate,
    event_date: datetime | None,
    sport: str,
    highlight_keywords: list[str] | None = None,
    official_channels: dict[str, list[str]] | None = None,
    major_networks: list[str] | None = None,
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
        highlight_keywords: Custom highlight keywords (defaults to common ones)
        official_channels: Dict mapping sport to list of official channel IDs
        major_networks: List of major sports network channel IDs
    
    Returns:
        Dictionary with scoring breakdown
    """
    if highlight_keywords is None:
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
    
    # 1. Highlight keyword detection
    text = f"{video.title} {video.description}".lower()
    keyword_matches = sum(1 for keyword in highlight_keywords if keyword in text)
    highlight_score = min(keyword_matches / 3.0, 1.0)  # Normalize to 0-1
    
    # 2. Channel reputation
    channel_reputation = get_channel_reputation_score(
        video.channel_id, sport, official_channels, major_networks
    )
    
    # 3. View count normalization (log scale)
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


def get_channel_reputation_score(
    channel_id: str,
    sport: str,
    official_channels: dict[str, list[str]] | None = None,
    major_networks: list[str] | None = None,
) -> float:
    """Calculate channel reputation score.
    
    Scoring:
    - Official league/team channels: 1.0
    - Major sports networks: 0.8
    - Others: 0.5
    
    Args:
        channel_id: YouTube channel ID
        sport: Sport name (for official channel lookup)
        official_channels: Dict mapping sport to list of official channel IDs
        major_networks: List of major sports network channel IDs
    
    Returns:
        Reputation score (0.0 - 1.0)
    """
    if official_channels:
        official_list = official_channels.get(sport.upper(), [])
        if channel_id in official_list:
            return 1.0
    
    if major_networks and channel_id in major_networks:
        return 0.8
    
    # Default score
    return 0.5


def calculate_general_video_score(
    video: VideoCandidate,
    keywords: list[str],
    target_duration_minutes: float | None = None,
    min_duration_minutes: float | None = None,
    max_duration_minutes: float | None = None,
) -> VideoScore:
    """Calculate score for general (non-sports) video playlist.
    
    Args:
        video: Video candidate
        keywords: Keywords to match against title/description
        target_duration_minutes: Target duration (for length fit scoring)
        min_duration_minutes: Minimum acceptable duration
        max_duration_minutes: Maximum acceptable duration
    
    Returns:
        Video score breakdown
    """
    # 1. Keyword matching
    text = f"{video.title} {video.description}".lower()
    keyword_lower = [kw.lower() for kw in keywords]
    keyword_hits = sum(1 for kw in keyword_lower if kw in text)
    keyword_score = min(keyword_hits / max(len(keywords), 1), 1.0)
    
    # 2. View count normalization
    if video.view_count > 0:
        log_views = math.log10(video.view_count + 1)
        view_count_normalized = min(log_views / 6.0, 1.0)  # ~1M views = 1.0
        view_count_normalized = max(view_count_normalized, 0.1)
    else:
        view_count_normalized = 0.1
    
    # 3. Freshness (based on publish date)
    age_days = (datetime.utcnow() - video.published_at).total_seconds() / (60 * 60 * 24)
    freshness_score = max(0, 1 - age_days / 720)  # Degrade after ~2 years
    
    # 4. Length fit
    length_fit = 1.0
    if target_duration_minutes or min_duration_minutes or max_duration_minutes:
        video_minutes = video.duration_seconds / 60.0
        
        if min_duration_minutes and video_minutes < min_duration_minutes:
            length_fit = 0.0
        elif max_duration_minutes and video_minutes > max_duration_minutes:
            length_fit = 0.0
        elif target_duration_minutes:
            # Score based on how close to target
            diff = abs(video_minutes - target_duration_minutes)
            length_fit = max(0, 1 - diff / target_duration_minutes)
    
    # 5. Channel reputation (default 0.5 for general videos)
    channel_reputation = 0.5
    
    # 6. Combined score
    final_score = (
        keyword_score * 3.0
        + view_count_normalized * 2.0
        + freshness_score * 1.5
        + length_fit * 1.5
        + (0.5 if video.view_count > 500_000 else 0.0)
    )
    
    return VideoScore(
        keyword_score=keyword_score,
        channel_reputation=channel_reputation,
        view_count_normalized=view_count_normalized,
        freshness_score=freshness_score,
        length_fit=length_fit,
        final_score=final_score,
    )

