"""Sports-focused YouTube search helpers for highlight playlists."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


@dataclass
class SportsSearchSpec:
    """Structured specification for sports video search."""

    sport: str  # NFL, NBA, MLB, NHL, NCAAF, NCAAB, PGA, F1, etc.
    league: str | None = None  # Optional league name
    teams: list[str] | None = None  # Optional team names
    players: list[str] | None = None  # Optional player names (e.g., ["Patrick Mahomes", "LeBron James"])
    play_types: list[str] | None = None  # Optional play types (e.g., ["touchdowns", "interceptions", "buzzer beaters"])
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


async def generate_ai_search_queries(
    spec: SportsSearchSpec,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
) -> list[str]:
    """Generate additional search query variations using AI.
    
    Args:
        spec: Sports search specification
        api_key: OpenAI API key (or from env)
        model: OpenAI model to use
    
    Returns:
        List of additional search query variations
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        # If no API key, return empty list (fallback to regular queries)
        return []
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Build context for query generation
        context_parts = [f"Sport: {spec.sport}"]
        if spec.players:
            context_parts.append(f"Players: {', '.join(spec.players)}")
        if spec.play_types:
            context_parts.append(f"Play types: {', '.join(spec.play_types)}")
        if spec.teams:
            context_parts.append(f"Teams: {', '.join(spec.teams)}")
        if spec.date_range:
            date_str = _format_date_for_query(spec.date_range)
            if date_str:
                context_parts.append(f"Date: {date_str}")
        
        system_prompt = """You are a search query generator for sports videos. Generate 5-8 diverse search query variations that would find relevant videos on YouTube.

Each query should:
- Be specific and targeted
- Use natural language that matches how sports videos are titled
- Cover different angles (player-focused, team-focused, play-type-focused)
- Include relevant keywords (highlights, top plays, etc.)

Return ONLY a JSON array of query strings, no explanations, no markdown."""
        
        user_prompt = f"""Generate search queries for: {', '.join(context_parts)}

Return a JSON array of 5-8 query strings."""
        
        # Run OpenAI call in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Higher temperature for diversity
                response_format={"type": "json_object"},
            )
        )
        
        content = response.choices[0].message.content
        if not content:
            return []
        
        parsed = json.loads(content)
        # Handle different response formats
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            # Look for common keys
            queries = parsed.get("queries", parsed.get("query", []))
            if isinstance(queries, list):
                return queries
            elif isinstance(queries, str):
                return [queries]
        
        return []
    except Exception:
        # If AI generation fails, return empty list (fallback to regular queries)
        return []


def build_search_queries(spec: SportsSearchSpec) -> list[str]:
    """Build YouTube search queries from structured spec.
    
    Uses query templates based on available information:
    - "{player} {play_type} {sport} {date}"
    - "{team} vs {opponent} highlights {date}"
    - "{league} highlights {date}"
    - "{sport} {play_type} {date}"
    - etc.
    
    Includes dates in query strings to help YouTube match videos with dates in titles.
    Also uses publishedAfter/publishedBefore for additional filtering.
    
    Args:
        spec: Structured search specification
    
    Returns:
        List of search query strings
    """
    queries: list[str] = []
    sport = spec.sport.upper()
    
    # Map sport codes to more searchable terms
    sport_search_terms = {
        "NCAAB": ["college basketball", "NCAAB", "NCAA basketball"],
        "NCAAF": ["college football", "NCAAF", "NCAA football"],
        "NFL": ["NFL", "football"],
        "NBA": ["NBA", "basketball"],
        "MLB": ["MLB", "baseball"],
        "NHL": ["NHL", "hockey"],
        "PGA": ["PGA", "golf", "PGA Tour", "professional golf", "golf highlights"],
        "LPGA": ["LPGA", "golf", "women's golf", "LPGA Tour"],
        "F1": ["F1", "Formula 1", "Formula One", "racing"],
        "SOCCER": ["soccer", "football", "football highlights"],
        "TENNIS": ["tennis", "ATP", "WTA"],
    }
    # Use sport-specific search terms, fallback to sport code
    sport_terms = sport_search_terms.get(sport, [sport])
    
    # Determine content type keywords
    content_keywords = spec.content_types or ["highlights"]
    
    # Format date string for query (e.g., "November 2024", "Week 9 2024", "2024")
    date_str = _format_date_for_query(spec.date_range)
    
    # Priority 1: Player + play type queries (most specific)
    if spec.players and spec.play_types:
        for player in spec.players:
            for play_type in spec.play_types:
                for content_type in content_keywords:
                    for sport_term in sport_terms:
                        if date_str:
                            query = f"{player} {play_type} {sport_term} {date_str} {content_type}"
                        else:
                            query = f"{player} {play_type} {sport_term} {content_type}"
                        queries.append(query)
    
    # Priority 2: Player-only queries
    if spec.players:
        for player in spec.players:
            for content_type in content_keywords:
                for sport_term in sport_terms:
                    if date_str:
                        query = f"{player} {sport_term} {date_str} {content_type}"
                    else:
                        query = f"{player} {sport_term} {content_type}"
                    queries.append(query)
    
    # Priority 3: Play type queries (without player) - make these more specific
    if spec.play_types:
        for play_type in spec.play_types:
            for content_type in content_keywords:
                for sport_term in sport_terms:
                    if date_str:
                        # Use more specific terms for play-type focused videos
                        query = f"{sport_term} {play_type} compilation {date_str} {content_type}"
                        queries.append(query)
                        query = f"{sport_term} {play_type} {date_str} {content_type}"
                        queries.append(query)
                        # Also try "best" or "top" for play types
                        query = f"best {sport_term} {play_type} {date_str}"
                        queries.append(query)
                    else:
                        query = f"{sport_term} {play_type} compilation {content_type}"
                        queries.append(query)
                        query = f"{sport_term} {play_type} {content_type}"
                        queries.append(query)
                        query = f"best {sport_term} {play_type}"
                        queries.append(query)
    
    # Priority 4: Team vs team queries
    if spec.teams and len(spec.teams) >= 2:
        team1, team2 = spec.teams[0], spec.teams[1]
        for content_type in content_keywords:
            for sport_term in sport_terms:
                if date_str:
                    query = f"{team1} vs {team2} {date_str} {content_type}"
                else:
                    query = f"{team1} vs {team2} {content_type}"
                queries.append(query)
    
    # Priority 5: League-specific queries
    if spec.league:
        for content_type in content_keywords:
            for sport_term in sport_terms:
                if date_str:
                    query = f"{spec.league} {date_str} {content_type}"
                else:
                    query = f"{spec.league} {content_type}"
                queries.append(query)
    
    # Priority 6: Sport-level query (fallback) - try all sport terms
    for content_type in content_keywords:
        for sport_term in sport_terms:
            if date_str:
                query = f"{sport_term} {date_str} {content_type}"
            else:
                query = f"{sport_term} {content_type}"
            queries.append(query)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)
    
    return unique_queries[:10]  # Increased limit to allow more query variations


def _format_date_for_query(date_range: dict[str, Any] | None) -> str:
    """Format date range for inclusion in YouTube search query.
    
    Delegates to centralized datetime utility, with additional handling for week/season.
    
    Args:
        date_range: Date range dict with start/end or single_date
    
    Returns:
        Formatted date string for query, or empty string
    """
    if not date_range:
        return ""
    
    # Handle week/season references (not in datetime_utils yet)
    try:
        if "week" in date_range:
            week = date_range.get("week", "")
            season = date_range.get("season", "")
            if week and season:
                return f"{week} {season}"  # "Week 9 2024"
            elif week:
                return week  # "Week 9"
        
        if "season" in date_range:
            return str(date_range["season"])  # "2024"
    except (KeyError, TypeError):
        pass
    
    # Delegate to centralized utility for standard date formatting
    from .utils.datetime_utils import format_date_for_query
    
    return format_date_for_query(date_range)


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
    players: list[str] | None = None,
    play_types: list[str] | None = None,
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
    # Prepare text for matching
    text = f"{video.title} {video.description}".lower()
    title_lower = video.title.lower()  # Define title_lower for play type matching
    
    # 0. Sport matching (CRITICAL - heavily penalize wrong sport)
    sport_match_score = 1.0
    sport_lower = sport.upper()
    
    # Sport-specific keywords that indicate wrong sport
    wrong_sport_indicators = {
        "PGA": ["nba", "basketball", "nfl", "football", "mlb", "baseball", "nhl", "hockey", "wwe", "wrestling", "ufc", "boxing", "tennis"],
        "NBA": ["golf", "pga", "nfl", "football", "mlb", "baseball", "nhl", "hockey", "wwe", "wrestling", "ufc", "boxing", "tennis"],
        "NFL": ["golf", "pga", "nba", "basketball", "mlb", "baseball", "nhl", "hockey", "wwe", "wrestling", "ufc", "boxing", "tennis"],
        "MLB": ["golf", "pga", "nba", "basketball", "nfl", "football", "nhl", "hockey", "wwe", "wrestling", "ufc", "boxing", "tennis"],
        "NHL": ["golf", "pga", "nba", "basketball", "nfl", "football", "mlb", "baseball", "wwe", "wrestling", "ufc", "boxing", "tennis"],
        "SOCCER": ["golf", "pga", "nba", "basketball", "nfl", "football", "mlb", "baseball", "nhl", "hockey", "wwe", "wrestling"],
        "TENNIS": ["golf", "pga", "nba", "basketball", "nfl", "football", "mlb", "baseball", "nhl", "hockey", "wwe", "wrestling"],
    }
    
    # Sport-specific keywords that indicate correct sport
    correct_sport_indicators = {
        "PGA": ["golf", "pga", "pga tour", "masters", "us open", "pga championship", "ryder cup", "tiger woods", "phil mickelson", "scottie scheffler"],
        "NBA": ["nba", "basketball", "lakers", "warriors", "celtics", "lebron", "curry", "durant"],
        "NFL": ["nfl", "football", "chiefs", "patriots", "mahomes", "brady", "touchdown", "super bowl"],
        "MLB": ["mlb", "baseball", "yankees", "dodgers", "home run", "world series"],
        "NHL": ["nhl", "hockey", "stanley cup", "goal", "puck"],
        "SOCCER": ["soccer", "football", "premier league", "champions league", "world cup", "goal"],
        "TENNIS": ["tennis", "wimbledon", "us open", "french open", "australian open", "atp", "wta"],
    }
    
    # Check for wrong sport indicators
    if sport_lower in wrong_sport_indicators:
        for wrong_indicator in wrong_sport_indicators[sport_lower]:
            if wrong_indicator in text:
                # Heavy penalty: wrong sport detected
                sport_match_score = 0.1
                break
    
    # Check for correct sport indicators (only if not already penalized)
    if sport_match_score > 0.1 and sport_lower in correct_sport_indicators:
        has_correct_indicator = False
        for correct_indicator in correct_sport_indicators[sport_lower]:
            if correct_indicator in text:
                has_correct_indicator = True
                break
        if not has_correct_indicator:
            # Moderate penalty: no clear sport match
            sport_match_score = 0.5
    
    # 1. Player and play type matching (CRITICAL - heavily penalize mismatches)
    player_match_score = 1.0
    play_type_match_score = 1.0
    
    if players:
        # Check if any player name appears in title/description
        player_found = False
        for player in players:
            # Try full name and last name only
            player_lower = player.lower()
            if player_lower in text:
                player_found = True
                break
            # Also try last name only (e.g., "Mahomes" from "Patrick Mahomes")
            last_name = player.split()[-1].lower() if " " in player else player_lower
            if last_name in text:
                player_found = True
                break
        
        if player_found:
            player_match_score = 1.0  # Perfect match
        else:
            # Heavy penalty: reduce score by 80% if player not found
            player_match_score = 0.2
    
    if play_types:
        # Check if any play type appears in title/description
        # For play types, we need STRONG matches - they should be the focus of the video
        play_type_found = False
        play_type_in_title = False
        
        for play_type in play_types:
            play_type_lower = play_type.lower()
            # Check title first (more important for play-type specific videos)
            if play_type_lower in title_lower:
                play_type_found = True
                play_type_in_title = True
                break
            # Check for singular/plural variations in title
            if play_type_lower.endswith("s"):
                singular = play_type_lower[:-1]
                if singular in title_lower:
                    play_type_found = True
                    play_type_in_title = True
                    break
            else:
                plural = play_type_lower + "s"
                if plural in title_lower:
                    play_type_found = True
                    play_type_in_title = True
                    break
            
            # Check description (less weight but still important)
            if play_type_lower in text:
                play_type_found = True
                break
            # Check for singular/plural variations in description
            if play_type_lower.endswith("s"):
                singular = play_type_lower[:-1]
                if singular in text:
                    play_type_found = True
                    break
            else:
                plural = play_type_lower + "s"
                if plural in text:
                    play_type_found = True
                    break
        
        if play_type_found:
            if play_type_in_title:
                play_type_match_score = 1.0  # Perfect match - play type in title
            else:
                play_type_match_score = 0.7  # Good match - play type in description only
        else:
            # Very heavy penalty: reduce score by 90% if play type not found
            # Play types are critical - if user asks for "interceptions", they want interceptions, not general highlights
            play_type_match_score = 0.1
    
    # 2. Highlight keyword detection
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
    keyword_matches = sum(1 for keyword in highlight_keywords if keyword in text)
    highlight_score = min(keyword_matches / 3.0, 1.0)  # Normalize to 0-1
    
    # 3. Channel reputation
    channel_reputation = get_channel_reputation_score(video.channel_id, sport)
    
    # 4. View count normalization (log scale)
    # Assume typical highlight videos get 10K-10M views
    if video.view_count > 0:
        log_views = math.log10(video.view_count + 1)
        # Normalize: 4 (10K) = 0.4, 7 (10M) = 1.0
        view_count_normalized = min((log_views - 3) / 4.0, 1.0)
        view_count_normalized = max(view_count_normalized, 0.1)  # Minimum 0.1
    else:
        view_count_normalized = 0.1
    
    # 5. Freshness score
    freshness_score = 1.0
    if event_date:
        # Ensure both datetimes are timezone-aware for comparison
        if video.published_at.tzinfo is None:
            video_published = video.published_at.replace(tzinfo=timezone.utc)
        else:
            video_published = video.published_at
        if event_date.tzinfo is None:
            event_dt = event_date.replace(tzinfo=timezone.utc)
        else:
            event_dt = event_date
        
        # Check if this is historical content (event date is more than 1 year ago)
        from .utils.datetime_utils import now_utc
        
        now = now_utc()
        years_since_event = (now - event_dt).days / 365.25
        
        if years_since_event > 1:
            # Historical content: don't penalize based on publish date
            # Videos about old events can be published anytime (retrospectives, compilations, etc.)
            freshness_score = 1.0
        else:
            # Recent content: score based on how close publish date is to event date
            # For recent highlights (catch-up use case), heavily penalize videos published >3 days after event
            days_diff = abs((video_published - event_dt).days)
            if days_diff == 0:
                freshness_score = 1.0  # Same day = perfect
            elif days_diff <= 1:
                freshness_score = 0.95  # Within 24 hours = excellent
            elif days_diff <= 2:
                freshness_score = 0.85  # Within 48 hours = very good (target window)
            elif days_diff <= 3:
                freshness_score = 0.6  # 3 days = acceptable but lower
            elif days_diff <= 7:
                freshness_score = 0.3  # Week old = low priority
            elif days_diff <= 30:
                freshness_score = 0.1  # Month old = very low
            else:
                freshness_score = 0.05  # Very old = almost reject
    
    # 6. Duration score (prefer 2-8 minute videos, exclude Shorts)
    duration_seconds = video.duration_seconds
    duration_score = 1.0
    
    # Optimal range: 2-8 minutes (120-480 seconds) = score 1.0
    if 120 <= duration_seconds <= 480:
        duration_score = 1.0
    # Sweet spot edges: 75s-120s and 480s-600s = score 0.8-1.0
    elif 75 <= duration_seconds < 120:
        # Linear interpolation: 75s = 0.8, 120s = 1.0
        duration_score = 0.8 + (duration_seconds - 75) / 45 * 0.2
    elif 480 < duration_seconds <= 600:
        # Linear interpolation: 480s = 1.0, 600s = 0.8
        duration_score = 1.0 - (duration_seconds - 480) / 120 * 0.2
    # Medium range: 600s-1200s (10-20 minutes) = score 0.6-0.8
    elif 600 < duration_seconds <= 1200:
        # Linear interpolation: 600s = 0.8, 1200s = 0.6
        duration_score = 0.8 - (duration_seconds - 600) / 600 * 0.2
    # Long tail: 1200s-1800s (20-30 minutes) = score 0.4-0.6
    elif 1200 < duration_seconds <= 1800:
        # Linear interpolation: 1200s = 0.6, 1800s = 0.4
        duration_score = 0.6 - (duration_seconds - 1200) / 600 * 0.2
    # Very long (>30 minutes) = score 0.2-0.4
    else:
        # Exponential decay for very long videos
        duration_score = max(0.2, 0.4 - (duration_seconds - 1800) / 3600 * 0.2)
    
    # 7. Channel quality boost (official channels get significant boost)
    channel_quality_boost = 1.0
    if channel_reputation >= 0.9:  # Official channels
        channel_quality_boost = 1.5  # 50% boost for official channels
    elif channel_reputation >= 0.7:  # Major networks
        channel_quality_boost = 1.2  # 20% boost for major networks
    
    # 8. Player/play type title boost (videos with matches in title get boost)
    title_boost = 1.0
    title_lower = video.title.lower()
    if players:
        for player in players:
            player_lower = player.lower()
            if player_lower in title_lower or (len(player.split()) > 1 and player.split()[-1].lower() in title_lower):
                title_boost = 1.3  # 30% boost for player in title
                break
    
    if play_types:
        for play_type in play_types:
            play_type_lower = play_type.lower()
            # Check for play type in title - this is critical for play-type queries
            if play_type_lower in title_lower:
                # Extra boost if it's a compilation or highlights focused on the play type
                if any(keyword in title_lower for keyword in ["compilation", "highlights", "best", "top", "all"]):
                    title_boost = max(title_boost, 1.5)  # 50% boost for play-type compilation in title
                else:
                    title_boost = max(title_boost, 1.3)  # 30% boost for play type in title
                break
            # Also check singular/plural
            if play_type_lower.endswith("s"):
                singular = play_type_lower[:-1]
                if singular in title_lower:
                    if any(keyword in title_lower for keyword in ["compilation", "highlights", "best", "top", "all"]):
                        title_boost = max(title_boost, 1.5)
                    else:
                        title_boost = max(title_boost, 1.3)
                    break
            else:
                plural = play_type_lower + "s"
                if plural in title_lower:
                    if any(keyword in title_lower for keyword in ["compilation", "highlights", "best", "top", "all"]):
                        title_boost = max(title_boost, 1.5)
                    else:
                        title_boost = max(title_boost, 1.3)
                    break
    
    # 9. Combined final score
    # Apply player and play type match scores as multipliers (critical filters)
    base_score = (
        highlight_score * 0.25
        + channel_reputation * 0.25
        + view_count_normalized * 0.2
        + freshness_score * 0.15
        + duration_score * 0.15
    )
    
    # Apply boosts and multipliers
    # Sport match score is critical - apply it first to heavily penalize wrong sport videos
    final_score = base_score * sport_match_score * player_match_score * play_type_match_score * channel_quality_boost * title_boost
    
    return {
        "highlight_score": highlight_score,
        "channel_reputation": channel_reputation,
        "view_count_normalized": view_count_normalized,
        "freshness_score": freshness_score,
        "duration_score": duration_score,
        "sport_match_score": sport_match_score,
        "player_match_score": player_match_score,
        "play_type_match_score": play_type_match_score,
        "final_score": final_score,
    }


async def search_youtube_sports(
    spec: SportsSearchSpec,
    api_key: str | None = None,
    max_results: int = 50,
    initial_search_limit: int = 250,
) -> tuple[list[VideoCandidate], int]:
    """Search YouTube for sports videos based on structured spec.
    
    Args:
        spec: Structured search specification
        api_key: YouTube Data API key (or from env)
        max_results: Maximum number of results to return (deprecated, use initial_search_limit)
        initial_search_limit: Maximum number of candidates to fetch initially (default 250)
    
    Returns:
        Tuple of (list of video candidates with scoring, number of YouTube API calls made)
    """
    api_key = api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("YouTube API key required (set YOUTUBE_API_KEY env var)")
    
    # Build search queries (base queries + AI-generated variations)
    base_queries = build_search_queries(spec)
    
    # Generate AI-powered query variations (non-blocking, fallback if fails)
    ai_queries = []
    try:
        ai_queries = await generate_ai_search_queries(spec, api_key)
        if ai_queries:
            # Log successful AI query generation
            # Note: Using basic logging here since this function doesn't have access to structured logger
            # The calling code in highlights.py will log at a higher level
            pass  # Success is implicit - queries are added to the list
    except Exception as e:
        # Log the failure but continue with base queries
        # Note: Using basic logging here since this function doesn't have access to structured logger
        # The calling code in highlights.py will log at a higher level
        # For now, we silently fall back to base queries (this is expected behavior)
        pass
    
    # Combine base and AI queries, prioritizing base queries
    queries = base_queries + ai_queries[:5]  # Limit AI queries to avoid too many
    
    # Determine duration filters based on content type
    duration_filters = get_duration_filters(spec.content_types or ["highlights"])
    
    all_candidates: list[VideoCandidate] = []
    seen_video_ids = set()
    api_call_count = 0  # Track YouTube API calls
    
    # Calculate results per query to reach initial_search_limit
    # Distribute across queries, but YouTube API max is 50 per request
    results_per_query = min(50, max(10, initial_search_limit // max(len(queries), 1)))
    total_needed = initial_search_limit
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in queries:
            # Stop if we have enough candidates
            if len(all_candidates) >= total_needed:
                break
                
            # Search API call
            remaining_needed = total_needed - len(all_candidates)
            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": min(50, results_per_query, remaining_needed),
                "order": "relevance",
                "key": api_key,
            }
            
            # Add date filters if we have a date range
            # Use a wider window to account for videos published after the event
            # Sports highlights are often published 1-3 days after the event
            if spec.date_range:
                if "start" in spec.date_range and "end" in spec.date_range:
                    # Use publishedAfter and publishedBefore for date filtering
                    # Format: RFC 3339 format (YYYY-MM-DDTHH:MM:SSZ)
                    start_date = spec.date_range["start"]
                    end_date = spec.date_range["end"]
                    try:
                        # Parse and format dates for YouTube API
                        start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
                        end_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
                        
                        # For historical content (more than 1 year ago), don't widen the window
                        # Historical videos can be published anytime (retrospectives, compilations)
                        from .utils.datetime_utils import now_utc
                        
                        now = now_utc()
                        start_dt_aware = start_dt.replace(tzinfo=timezone.utc) if start_dt.tzinfo is None else start_dt
                        years_since_start = (now - start_dt_aware).days / 365.25
                        
                        if years_since_start > 1:
                            # Historical: use exact date range (videos can be published anytime)
                            pass  # Don't widen window
                        else:
                            # Recent highlights: widen window but keep it tight for catch-up use case
                            # Start 1 day before (for previews), end 3 days after (highlights typically uploaded within 48h)
                            start_dt = start_dt - timedelta(days=1)
                            end_dt = end_dt + timedelta(days=3)  # Tight window: highlights usually uploaded within 48h
                        
                        # Format as RFC 3339
                        search_params["publishedAfter"] = start_dt.strftime("%Y-%m-%dT00:00:00Z")
                        search_params["publishedBefore"] = end_dt.strftime("%Y-%m-%dT23:59:59Z")
                    except (ValueError, AttributeError, TypeError):
                        # If date parsing fails, skip date filters
                        pass
                elif "date" in spec.date_range:
                    # Single date - widen window to ±4 days to account for late publishing
                    single_date = spec.date_range["date"]
                    try:
                        date_dt = datetime.fromisoformat(single_date) if isinstance(single_date, str) else single_date
                        start_dt = date_dt - timedelta(days=4)  # Start 4 days before
                        end_dt = date_dt + timedelta(days=4)  # End 4 days after
                        search_params["publishedAfter"] = start_dt.strftime("%Y-%m-%dT00:00:00Z")
                        search_params["publishedBefore"] = end_dt.strftime("%Y-%m-%dT23:59:59Z")
                    except (ValueError, AttributeError, TypeError):
                        pass
            
            # Add channel filter if we have official channels
            official_channels = OFFICIAL_CHANNELS.get(spec.sport.upper(), [])
            if official_channels:
                # Prefer official channels but don't restrict
                pass  # Could add channelId filter here if needed
            
            search_url = "https://www.googleapis.com/youtube/v3/search"
            try:
                search_response = await retry_youtube_api_call(client, search_url, search_params)
                api_call_count += 1  # Count search API call
                search_data = search_response.json()
            except httpx.HTTPStatusError as e:
                # Re-raise with more context
                if e.response.status_code == 429:
                    raise ValueError(
                        "YouTube API rate limit exceeded. Please try again in a few minutes."
                    ) from e
                elif e.response.status_code == 403:
                    error_data = e.response.json() if e.response.content else {}
                    error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
                    if "quotaExceeded" in error_reason:
                        raise ValueError(
                            "YouTube API quota exceeded. Please try again later."
                        ) from e
                    raise ValueError(
                        f"YouTube API access denied: {error_reason or 'Invalid API key or permissions'}"
                    ) from e
                raise ValueError(f"YouTube API error: {e.response.status_code}") from e
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                raise ValueError(
                    f"Network error connecting to YouTube API: {str(e)}. Please check your internet connection and try again."
                ) from e
            
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
            try:
                videos_response = await retry_youtube_api_call(client, videos_url, videos_params)
                api_call_count += 1  # Count videos API call
                videos_data = videos_response.json()
            except httpx.HTTPStatusError as e:
                # Re-raise with more context
                if e.response.status_code == 429:
                    raise ValueError(
                        "YouTube API rate limit exceeded. Please try again in a few minutes."
                    ) from e
                elif e.response.status_code == 403:
                    error_data = e.response.json() if e.response.content else {}
                    error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
                    if "quotaExceeded" in error_reason:
                        raise ValueError(
                            "YouTube API quota exceeded. Please try again later."
                        ) from e
                    raise ValueError(
                        f"YouTube API access denied: {error_reason or 'Invalid API key or permissions'}"
                    ) from e
                raise ValueError(f"YouTube API error: {e.response.status_code}") from e
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                raise ValueError(
                    f"Network error connecting to YouTube API: {str(e)}. Please check your internet connection and try again."
                ) from e
            
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
                    from .utils.datetime_utils import now_utc
                    
                    published_at = now_utc()
                
                # Get event date from spec (normalize to UTC timezone-aware)
                event_date = None
                if spec.date_range:
                    if "date" in spec.date_range:
                        try:
                            # Parse date and make it timezone-aware (UTC, midnight)
                            date_str = spec.date_range["date"]
                            event_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
                        except (ValueError, AttributeError):
                            pass
                    elif "start" in spec.date_range:
                        try:
                            # Parse date and make it timezone-aware (UTC, midnight)
                            date_str = spec.date_range["start"]
                            event_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
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
                
                if len(all_candidates) >= initial_search_limit:
                    break
            
            if len(all_candidates) >= initial_search_limit:
                break
    
    # Score and sort candidates
    scored_candidates = []
    for candidate in all_candidates:
        scores = calculate_highlight_score(
            candidate, event_date, spec.sport, spec.players, spec.play_types
        )
        
        # Hard filter: Sport match is CRITICAL - exclude videos that don't match the sport
        sport_match = scores.get("sport_match_score", 1.0)
        if sport_match < 0.3:
            continue  # Skip videos that clearly don't match the sport
        
        # Hard filter: If we have players or play_types specified, exclude videos that don't match
        # (unless the match score is at least 0.3, meaning it might be a partial match)
        if spec.players or spec.play_types:
            player_match = scores.get("player_match_score", 1.0)
            play_type_match = scores.get("play_type_match_score", 1.0)
            
            # If both are specified and both fail, exclude
            if spec.players and spec.play_types:
                if player_match < 0.3 and play_type_match < 0.5:
                    continue  # Skip this video entirely - play types need stronger match
            # If only players specified and no match, exclude
            elif spec.players and player_match < 0.3:
                continue
            # If only play_types specified, require stronger match (0.5 = at least in description)
            # This ensures we get play-type focused videos, not general game highlights
            elif spec.play_types and play_type_match < 0.5:
                continue
        
        scored_candidates.append((candidate, scores))
    
    # Sort by final_score descending
    scored_candidates.sort(key=lambda x: x[1]["final_score"], reverse=True)
    
    # Return all candidates (not just top N) for further processing
    # The caller will handle filtering and selection
    return [candidate for candidate, _ in scored_candidates], api_call_count


async def retry_youtube_api_call(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> httpx.Response:
    """Retry YouTube API call with exponential backoff for transient failures.
    
    Args:
        client: httpx async client
        url: API endpoint URL
        params: Request parameters
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
    
    Returns:
        httpx.Response object
    
    Raises:
        httpx.HTTPStatusError: For non-retryable errors (4xx except 429, 5xx)
        httpx.RequestError: For network errors after all retries
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            response = await client.get(url, params=params, timeout=30.0)
            
            # Don't retry on success
            if response.status_code < 400:
                return response
            
            # Don't retry on client errors (except 429 which is handled separately)
            if 400 <= response.status_code < 500 and response.status_code != 429:
                response.raise_for_status()
                return response
            
            # Retry on 429 (rate limit) and 5xx (server errors)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < max_retries:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    delay = initial_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    response.raise_for_status()
                    return response
            
            # For other status codes, raise immediately
            response.raise_for_status()
            return response
            
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
            last_error = e
            if attempt < max_retries:
                # Exponential backoff for network errors
                delay = initial_delay * (2 ** attempt)
                await asyncio.sleep(delay)
                continue
            else:
                raise
    
    # Should never reach here, but just in case
    if last_error:
        raise last_error
    raise httpx.RequestError("Failed to complete request after retries")


def get_duration_filters(content_types: list[str]) -> dict[str, tuple[int, int | None]]:
    """Get duration filter ranges based on content types.
    
    Excludes YouTube Shorts (videos under 75 seconds).
    Allows videos up to ~30 minutes (1800 seconds) with preference for 2-8 minute videos.
    
    Args:
        content_types: List of content types (highlights, bloopers, etc.)
    
    Returns:
        Dictionary mapping content type to (min_seconds, max_seconds)
    """
    filters: dict[str, tuple[int, int | None]] = {}
    
    # Minimum 75 seconds to exclude YouTube Shorts
    MIN_DURATION = 75
    # Maximum ~30 minutes for long highlight packages
    MAX_DURATION = 1800
    
    for content_type in content_types:
        content_lower = content_type.lower()
        if "top plays" in content_lower or "bloopers" in content_lower:
            filters[content_type] = (MIN_DURATION, 300)  # 75s - 5 minutes
        elif "highlights" in content_lower or "condensed" in content_lower:
            filters[content_type] = (MIN_DURATION, MAX_DURATION)  # 75s - 30 minutes
        elif "full game" in content_lower:
            filters[content_type] = (3600, None)  # > 1 hour
        else:
            filters[content_type] = (MIN_DURATION, MAX_DURATION)  # 75s - 30 minutes default
    
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

