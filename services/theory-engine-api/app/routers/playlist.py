"""Playlist-specific router with YouTube search and scoring."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from py_core import Domain, TheoryRequest, fetch_youtube_context

router = APIRouter(prefix="/api/theory", tags=["playlist"])


class PlaylistRequest(BaseModel):
    """Extended request for playlist generation."""

    text: str = Field(..., description="Topic description (e.g., 'Titanic but not the movie')")
    domain: Domain = Field(default=Domain.playlist)
    user_tier: str | None = None
    length: str = Field(default="30_60", description="Length bucket")
    sportsMode: bool = Field(default=False, description="Hide spoilers")
    keepEndingHidden: bool = Field(default=False, description="Delay ending reveals")
    endingDelayChoice: str | None = Field(default=None, description="When to reveal ending")


class VideoData(BaseModel):
    """Video data matching frontend format."""

    id: str
    title: str
    description: str
    durationSeconds: int
    publishedAt: str
    viewCount: int
    channelTitle: str
    tags: list[str]
    url: str
    score: float
    keywordHits: list[str]
    tag: str = Field(description="intro/context/deep_dive/ending/misc")


class PlaylistSegment(BaseModel):
    """Playlist segment matching frontend format."""

    video: VideoData
    lockedUntilMinute: int | None = None
    startsAtMinute: int | None = None


class PlaylistResponse(BaseModel):
    """Playlist generation response matching frontend format."""

    canonicalTopic: str
    totalDurationSeconds: int
    playlistTitle: str
    playlistLink: str | None = None
    segments: list[PlaylistSegment]
    endingDelayMinutes: int | None = None
    metadata: dict[str, Any]


def score_video_relevance(video: dict[str, Any], query: str, excluded_terms: list[str]) -> tuple[float, bool]:
    """Score video relevance and check exclusion compliance.
    
    Returns:
        (relevance_score, exclusion_compliant)
    """
    title_lower = video.get("title", "").lower()
    desc_lower = video.get("description", "").lower()
    query_lower = query.lower()
    
    # Check exclusion compliance
    exclusion_compliant = True
    for term in excluded_terms:
        if term.lower() in title_lower or term.lower() in desc_lower:
            exclusion_compliant = False
            break
    
    # Simple relevance scoring (keyword matching)
    query_words = set(query_lower.split())
    title_words = set(title_lower.split())
    desc_words = set(desc_lower.split())
    
    title_overlap = len(query_words & title_words) / max(len(query_words), 1)
    desc_overlap = len(query_words & desc_words) / max(len(query_words), 1)
    
    relevance = (title_overlap * 0.7) + (desc_overlap * 0.3)
    
    return relevance, exclusion_compliant


def score_recency(published_at: str | None) -> float:
    """Score video recency with exponential decay.
    
    Older videos get lower scores. Returns 0-1.
    """
    if not published_at:
        return 0.5  # Neutral if no date
    
    try:
        # Parse ISO date or similar
        pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(pub_date.tzinfo)
        days_old = (now - pub_date).days
        
        # Exponential decay: 1.0 for today, ~0.5 at 30 days, ~0.1 at 90 days
        decay_factor = 0.95
        score = decay_factor ** days_old
        return max(0.1, min(1.0, score))
    except Exception:
        return 0.5


def extract_excluded_terms(query: str) -> list[str]:
    """Extract exclusion terms from query (e.g., 'Titanic but not the movie')."""
    excluded: list[str] = []
    query_lower = query.lower()
    
    # Simple patterns: "but not X", "exclude X", "no X"
    if "but not" in query_lower:
        parts = query_lower.split("but not")
        if len(parts) > 1:
            excluded.extend([t.strip() for t in parts[1].split(",")])
    if "exclude" in query_lower:
        parts = query_lower.split("exclude")
        if len(parts) > 1:
            excluded.extend([t.strip() for t in parts[1].split(",")])
    if "no " in query_lower:
        # Extract after "no "
        idx = query_lower.find("no ")
        if idx >= 0:
            after_no = query_lower[idx + 3:].strip()
            excluded.extend([t.strip() for t in after_no.split(",")])
    
    return [t for t in excluded if t]


@router.post("/playlist", response_model=PlaylistResponse)
async def generate_playlist(req: PlaylistRequest) -> PlaylistResponse:
    """Generate a YouTube playlist with scoring."""
    
    excluded_terms = extract_excluded_terms(req.text)
    
    # Fetch YouTube context (this would hit real API in production)
    context = fetch_youtube_context(req.text, limit=20)
    
    # Mock video data structure (replace with real YouTube API response)
    mock_videos: list[dict[str, Any]] = [
        {
            "id": f"video_{i}",
            "title": f"Video {i} about {req.text}",
            "channelTitle": f"Channel {i}",
            "url": f"https://youtube.com/watch?v=video_{i}",
            "durationSeconds": 300 + (i * 60),
            "publishedAt": (datetime.now() - timedelta(days=i * 7)).isoformat(),
            "description": f"Description for video {i}",
        }
        for i in range(10)
    ]
    
    # Score and rank videos
    scored_videos: list[tuple[dict[str, Any], float, bool, float]] = []
    for video in mock_videos:
        relevance, exclusion_compliant = score_video_relevance(video, req.text, excluded_terms)
        recency = score_recency(video.get("publishedAt"))
        
        # Combined score: relevance * recency, penalize exclusion violations
        combined_score = relevance * recency
        if not exclusion_compliant:
            combined_score *= 0.1  # Heavy penalty
        
        scored_videos.append((video, combined_score, exclusion_compliant, recency))
    
    # Sort by combined score (descending)
    scored_videos.sort(key=lambda x: x[1], reverse=True)
    
    # Take top videos and classify
    segments: list[PlaylistSegment] = []
    total_duration = 0
    for idx, (video, score, exclusion_compliant, recency) in enumerate(scored_videos[:15]):
        # Simple classification: intro (first 2), context (next 3), deep_dive (middle), ending (last 2)
        if idx < 2:
            tag = "intro"
        elif idx < 5:
            tag = "context"
        elif idx >= len(scored_videos) - 2:
            tag = "ending"
        else:
            tag = "deep_dive"
        
        # Extract keyword hits (simple word matching)
        query_words = set(req.text.lower().split())
        title_words = set(video["title"].lower().split())
        keyword_hits = list(query_words & title_words)
        
        video_data = VideoData(
            id=video["id"],
            title=video["title"],
            description=video.get("description", ""),
            durationSeconds=video["durationSeconds"],
            publishedAt=video.get("publishedAt", datetime.now().isoformat()),
            viewCount=video.get("viewCount", 0),
            channelTitle=video["channelTitle"],
            tags=video.get("tags", []),
            url=video["url"],
            score=score,
            keywordHits=keyword_hits,
            tag=tag,
        )
        
        segments.append(PlaylistSegment(video=video_data))
        total_duration += video["durationSeconds"]
    
    # Generate playlist title
    playlist_title = f"Curated: {req.text[:50]}"
    
    # Compute ending delay in minutes
    ending_delay_minutes: int | None = None
    if req.keepEndingHidden and req.endingDelayChoice:
        if req.endingDelayChoice == "1h":
            ending_delay_minutes = 60
        elif req.endingDelayChoice == "2h":
            ending_delay_minutes = 120
        elif req.endingDelayChoice == "3h":
            ending_delay_minutes = 180
        elif req.endingDelayChoice == "5h":
            ending_delay_minutes = 300
        elif req.endingDelayChoice == "surprise":
            ending_delay_minutes = 90  # 60-120 min range, use 90 as default
    
    return PlaylistResponse(
        canonicalTopic=req.text,
        playlistTitle=playlist_title,
        playlistLink=None,  # Would be set if YouTube OAuth is configured
        totalDurationSeconds=total_duration,
        endingDelayMinutes=ending_delay_minutes,
        segments=segments,
        metadata={
            "requestedBucket": req.length,
            "sportsMode": req.sportsMode,
            "endingDelayChoice": req.endingDelayChoice,
            "keepEndingHidden": req.keepEndingHidden,
        },
    )

