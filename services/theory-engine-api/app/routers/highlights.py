"""Highlights API router for sports highlight playlists."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..db import get_async_session
from ..db_models import Playlist, PlaylistMode, PlaylistQuery
from ..highlight_parser import parse_highlight_request
from ..playlist_helpers import generate_normalized_signature, PlaylistQuerySpec
from ..logging_config import get_logger
from ..metrics import (
    get_sports_request_counts,
    get_average_playlist_duration,
    get_cache_hit_rate,
    export_metrics_csv,
)
from py_core.playlist.staleness import compute_stale_after, should_refresh_playlist
from ..sports_search import SportsSearchSpec, search_youtube_sports, calculate_highlight_score
from py_core.guardrails.sports_highlights import (
    check_sports_highlight_guardrails,
    has_hard_block_sports,
    normalize_sports_request,
)
from py_core.schemas.highlight_request import HighlightRequestSpec, Sport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/highlights", tags=["highlights"])
logger = get_logger(__name__)


class HighlightErrorResponse(BaseModel):
    """Error response with user-friendly message and error code."""

    error_code: str = Field(description="Error code for frontend handling")
    message: str = Field(description="User-friendly error message")
    detail: str | None = Field(default=None, description="Additional details or suggestions")
    retry_after: int | None = Field(default=None, description="Seconds to wait before retry (for rate limits)")


class HighlightPlanRequest(BaseModel):
    """Request to plan a highlight playlist."""

    query_text: str = Field(..., min_length=5, description="User query text")
    mode: PlaylistMode = Field(default=PlaylistMode.sports_highlight, description="Playlist mode")
    user_id: str | None = Field(default=None, description="Optional user ID (anonymous if not provided)")


class HighlightPlanResponse(BaseModel):
    """Response from planning a highlight playlist."""

    playlist_id: int
    query_id: int
    items: list[dict[str, Any]]
    total_duration_seconds: int
    cache_status: str = Field(description="'cached' or 'fresh'")
    explanation: dict[str, Any]
    created_at: str
    stale_after: str | None
    disclaimer: str = Field(
        default="This app builds playlists using public YouTube videos. We do not host or control the content.",
        description="Legal disclaimer about content source",
    )


class HighlightDetailResponse(BaseModel):
    """Detailed playlist response."""

    playlist_id: int
    query_id: int
    query_text: str
    items: list[dict[str, Any]]
    total_duration_seconds: int
    explanation: dict[str, Any]
    created_at: str
    stale_after: str | None
    query_metadata: dict[str, Any]
    disclaimer: str = Field(
        default="This app builds playlists using public YouTube videos. We do not host or control the content.",
        description="Legal disclaimer about content source",
    )


def convert_highlight_spec_to_search_spec(spec: HighlightRequestSpec) -> SportsSearchSpec:
    """Convert HighlightRequestSpec to SportsSearchSpec for search."""
    # Convert content mix to content types
    content_types = []
    if spec.content_mix.highlights > 0:
        content_types.append("highlights")
    if spec.content_mix.bloopers > 0:
        content_types.append("bloopers")
    if spec.content_mix.top_plays > 0:
        content_types.append("top plays")
    if spec.content_mix.condensed > 0:
        content_types.append("condensed")
    if spec.content_mix.full_game > 0:
        content_types.append("full game")
    if spec.content_mix.upsets > 0:
        content_types.append("upsets")
    if not content_types:
        content_types = ["highlights"]  # Default
    
    # Convert date range
    date_range = None
    if spec.date_range:
        if spec.date_range.single_date:
            date_range = {"date": spec.date_range.single_date}
        elif spec.date_range.start_date and spec.date_range.end_date:
            date_range = {"start": spec.date_range.start_date, "end": spec.date_range.end_date}
        elif spec.date_range.start_date:
            date_range = {"date": spec.date_range.start_date}
    
    return SportsSearchSpec(
        sport=spec.sport.value if isinstance(spec.sport, Sport) else spec.sport,
        league=spec.leagues[0] if spec.leagues else None,
        teams=spec.teams if spec.teams else None,
        date_range=date_range,
        content_types=content_types,
        duration_target_minutes=10,  # Default target per video
    )


def build_playlist_from_candidates(
    candidates: list[Any],
    requested_duration_minutes: int,
    spec: HighlightRequestSpec,
    search_spec: SportsSearchSpec,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build playlist items from video candidates.
    
    Selects videos to reach requested duration ± tolerance.
    
    Args:
        candidates: List of VideoCandidate objects from search (already sorted by score)
        requested_duration_minutes: Target duration
        spec: Highlight request spec
        search_spec: Sports search spec used for search
    
    Returns:
        Tuple of (playlist_items, explanation_dict)
    """
    target_seconds = requested_duration_minutes * 60
    tolerance = target_seconds * 0.1  # 10% tolerance
    
    selected_items: list[dict[str, Any]] = []
    total_duration = 0
    coverage_notes: list[str] = []
    
    # Get event date for scoring
    event_date = None
    if spec.date_range and spec.date_range.single_date:
        try:
            event_date = datetime.fromisoformat(spec.date_range.single_date)
        except (ValueError, AttributeError):
            pass
    elif spec.date_range and spec.date_range.start_date:
        try:
            event_date = datetime.fromisoformat(spec.date_range.start_date)
        except (ValueError, AttributeError):
            pass
    
    # Get sport name for scoring
    sport_name = search_spec.sport
    
    # Candidates are already sorted by final_score from search_youtube_sports
    for candidate in candidates:
        if total_duration >= target_seconds + tolerance:
            break
        
        # Calculate scores (recalculate for explanation)
        scores = calculate_highlight_score(candidate, event_date, sport_name)
        
        item = {
            "video_id": candidate.video_id,
            "title": candidate.title,
            "description": candidate.description[:500],  # Truncate long descriptions
            "channel_id": candidate.channel_id,
            "channel_title": candidate.channel_title,
            "duration_seconds": candidate.duration_seconds,
            "published_at": candidate.published_at.isoformat(),
            "view_count": candidate.view_count,
            "url": f"https://www.youtube.com/watch?v={candidate.video_id}",
            "thumbnail_url": candidate.thumbnail_url,
            "scores": scores,
            "tags": candidate.tags or [],
        }
        
        selected_items.append(item)
        total_duration += candidate.duration_seconds
    
    # Check if we reached target
    if total_duration < target_seconds - tolerance:
        coverage_notes.append(
            f"Only found {total_duration // 60} minutes of content (target: {requested_duration_minutes} minutes). "
            f"Consider expanding search criteria."
        )
    
    # Build explanation
    content_types_used = []
    if spec.content_mix.highlights > 0:
        content_types_used.append("highlights")
    if spec.content_mix.bloopers > 0:
        content_types_used.append("bloopers")
    if spec.content_mix.top_plays > 0:
        content_types_used.append("top plays")
    if spec.content_mix.condensed > 0:
        content_types_used.append("condensed")
    if spec.content_mix.full_game > 0:
        content_types_used.append("full game")
    if spec.content_mix.upsets > 0:
        content_types_used.append("upsets")
    if not content_types_used:
        content_types_used = ["highlights"]  # Default
    
    explanation = {
        "assumptions": spec.assumptions,
        "filters_applied": {
            "content_types": content_types_used,
            "exclusions": spec.exclusions,
            "nsfw_filter": spec.nsfw_filter,
        },
        "ranking_factors": {
            "highlight_score_weight": 0.3,
            "channel_reputation_weight": 0.3,
            "view_count_weight": 0.2,
            "freshness_weight": 0.2,
        },
        "coverage_notes": coverage_notes,
        "total_candidates": len(candidates),
        "selected_videos": len(selected_items),
        "actual_duration_minutes": round(total_duration / 60, 1),
        "target_duration_minutes": requested_duration_minutes,
    }
    
    return selected_items, explanation


def validate_highlight_request(request: HighlightPlanRequest) -> list[str]:
    """Validate highlight request and return list of validation errors.
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check query length
    if len(request.query_text.strip()) < 5:
        errors.append("Query must be at least 5 characters long")
    
    # Check for obviously invalid queries
    query_lower = request.query_text.lower()
    
    # Check for common mistakes
    if len(request.query_text.strip()) > 500:
        errors.append("Query is too long (max 500 characters). Please shorten your request.")
    
    # Check for suspicious patterns (could indicate abuse)
    suspicious_patterns = ["http://", "https://", "<script", "javascript:"]
    for pattern in suspicious_patterns:
        if pattern in query_lower:
            errors.append("Query contains invalid characters or patterns")
            break
    
    return errors


@router.post("/plan", response_model=HighlightPlanResponse, status_code=status.HTTP_201_CREATED)
async def plan_highlight_playlist(
    request: HighlightPlanRequest,
    http_request: Request,
) -> HighlightPlanResponse:
    """Plan a sports highlight playlist from user query.
    
    Steps:
    1. Validate request
    2. Run guardrails
    3. Call AI planner => structured spec
    4. Compute normalized_signature
    5. Check DB for existing not-stale playlist
    6. If found: return cached
    7. If not: build playlist, save, return fresh
    """
    # Validate request
    validation_errors = validate_highlight_request(request)
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=json.dumps({
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid request. Please check your query and try again.",
                "detail": "; ".join(validation_errors),
                "errors": validation_errors,
            }),
            headers={"Content-Type": "application/json"},
        )
    
    # Generate or use user ID for logging
    user_id = request.user_id or http_request.headers.get("X-User-ID") or f"anonymous_{uuid.uuid4().hex[:8]}"
    request_id = uuid.uuid4().hex
    
    # Start logging context
    log = logger.bind(
        request_id=request_id,
        user_id=user_id,
        query_text=request.query_text[:200],  # Truncate for logging
        mode=request.mode.value,
    )
    
    log.info("highlight_playlist_request_started")
    
    # Step 1: Normalize and check guardrails
    normalized_text = normalize_sports_request(request.query_text)
    guardrail_results = check_sports_highlight_guardrails(normalized_text, request.mode)
    
    if has_hard_block_sports(guardrail_results):
        log.warning(
            "highlight_playlist_guardrail_blocked",
            guardrail_flags=[r.code for r in guardrail_results],
        )
        # Get guardrail messages
        guardrail_messages = [r.message for r in guardrail_results if r.code.startswith("hard:")]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=json.dumps({
                "error_code": "GUARDRAIL_BLOCKED",
                "message": "This request cannot be processed due to content restrictions.",
                "detail": guardrail_messages[0] if guardrail_messages else "Your request violates our content policies.",
                "suggestions": [
                    "Try requesting highlights from official channels only",
                    "Avoid requesting full game reuploads or copyrighted broadcasts",
                    "Use general terms like 'highlights' or 'top plays' instead of specific copyrighted content",
                ],
            }),
            headers={"Content-Type": "application/json"},
        )
    
    # Step 2: Parse with AI
    try:
        parse_result = await parse_highlight_request(normalized_text)
        spec = parse_result.spec
    except ValueError as e:
        # User-friendly parsing errors
        error_msg = str(e)
        if "API key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=json.dumps({
                    "error_code": "CONFIGURATION_ERROR",
                    "message": "Service configuration error. Please contact support.",
                    "detail": "There was an issue with the AI parsing service.",
                }),
                headers={"Content-Type": "application/json"},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=json.dumps({
                "error_code": "PARSE_ERROR",
                "message": "Unable to understand your request. Please try rephrasing your query.",
                "detail": "We couldn't parse your request. Try being more specific about the sport, date, or content type.",
                "suggestions": [
                    "Include a sport name (e.g., NFL, NBA, MLB)",
                    "Specify a time period (e.g., 'last night', 'this week', 'November 2024')",
                    "Be clear about what you want (e.g., 'highlights', 'bloopers', 'top plays')",
                ],
            }),
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        log.error("highlight_playlist_parse_error", error=str(e), error_type=type(e).__name__, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=json.dumps({
                "error_code": "PARSE_ERROR",
                "message": "An error occurred while processing your request. Please try again.",
                "detail": "If this problem persists, please contact support.",
            }),
            headers={"Content-Type": "application/json"},
        )
    
    # Extract metadata early for use in cache check and query creation
    sport_name = spec.sport.value if isinstance(spec.sport, Sport) else spec.sport
    league_name = spec.leagues[0] if spec.leagues else None
    teams_list = spec.teams if spec.teams else None
    
    # Extract event_date
    event_date = None
    if spec.date_range and spec.date_range.single_date:
        try:
            event_date = datetime.fromisoformat(spec.date_range.single_date)
        except (ValueError, AttributeError):
            pass
    elif spec.date_range and spec.date_range.start_date:
        try:
            event_date = datetime.fromisoformat(spec.date_range.start_date)
        except (ValueError, AttributeError):
            pass
    
    # Try to infer is_playoff from query text or assumptions
    is_playoff = None
    if spec.assumptions:
        assumptions_text = " ".join(spec.assumptions).lower()
        if any(term in assumptions_text for term in ["playoff", "postseason", "championship", "finals", "super bowl"]):
            is_playoff = True
    
    # Step 3: Compute normalized signature
    # Convert HighlightRequestSpec to PlaylistQuerySpec for signature generation
    query_spec = PlaylistQuerySpec(
        sport=sport_name,
        leagues=spec.leagues,
        teams=teams_list,
        date_range=spec.date_range.model_dump() if spec.date_range else None,
        mix=[ct for ct in ["highlights", "bloopers", "top_plays"] if getattr(spec.content_mix, ct, 0) > 0],
        duration_bucket=None,  # Not used in signature
        exclusions=spec.exclusions,
        language=spec.language,
        mode=request.mode,
    )
    normalized_signature = generate_normalized_signature(query_spec)
    
    log = log.bind(
        normalized_signature=normalized_signature,
        sport=sport_name,
        requested_duration_minutes=spec.requested_duration_minutes,
    )
    
    # Step 4: Check DB for existing not-stale playlist
    async with get_async_session() as session:
        # Find query by signature
        query_stmt = select(PlaylistQuery).where(
            PlaylistQuery.normalized_signature == normalized_signature,
            PlaylistQuery.mode == request.mode,
        )
        result = await session.execute(query_stmt)
        existing_query = result.scalar_one_or_none()
        
        if existing_query:
            # Check for non-stale playlist
            playlist_stmt = select(Playlist).where(Playlist.query_id == existing_query.id).order_by(Playlist.created_at.desc())
            playlist_result = await session.execute(playlist_stmt)
            existing_playlist = playlist_result.scalar_one_or_none()
            
            if existing_playlist:
                # Check if stale
                now = datetime.utcnow()
                if not should_refresh_playlist(
                    existing_playlist.created_at,
                    existing_playlist.stale_after,
                    now,
                    force_refresh=False,
                    schema_version_changed=False,
                ):
                    # Update metadata if it's missing (for backward compatibility)
                    if existing_query.sport is None and sport_name:
                        existing_query.sport = sport_name
                        existing_query.league = league_name
                        existing_query.teams = teams_list
                        existing_query.event_date = event_date
                        existing_query.is_playoff = is_playoff
                        await session.commit()
                    # Return cached playlist
                    await session.commit()
                    
                    # Log cache hit
                    actual_duration_minutes = existing_playlist.total_duration_seconds / 60
                    log.info(
                        "highlight_playlist_cache_hit",
                        playlist_id=existing_playlist.id,
                        query_id=existing_query.id,
                        cache_status="cached",
                        actual_duration_minutes=round(actual_duration_minutes, 1),
                        requested_duration_minutes=spec.requested_duration_minutes,
                        duration_delta_minutes=round(actual_duration_minutes - spec.requested_duration_minutes, 1),
                        youtube_api_calls=0,  # No API calls for cache hit
                    )
                    
                    return HighlightPlanResponse(
                        playlist_id=existing_playlist.id,
                        query_id=existing_query.id,
                        items=existing_playlist.items,
                        total_duration_seconds=existing_playlist.total_duration_seconds,
                        cache_status="cached",
                        explanation=existing_playlist.explanation,
                        created_at=existing_playlist.created_at.isoformat(),
                        stale_after=existing_playlist.stale_after.isoformat() if existing_playlist.stale_after else None,
                        disclaimer="This app builds playlists using public YouTube videos. We do not host or control the content.",
                    )
        
        # Step 5: Build new playlist (sync for MVP)
        # Convert spec to search spec
        search_spec = convert_highlight_spec_to_search_spec(spec)
        
        # Search YouTube
        try:
            candidates, youtube_api_calls = await search_youtube_sports(search_spec, max_results=100)
            
            # Handle empty results
            if not candidates or len(candidates) == 0:
                log.warning(
                    "highlight_playlist_no_videos_found",
                    query_text=request.query_text,
                    sport=spec.sport.value if hasattr(spec.sport, 'value') else str(spec.sport),
                    date_range=spec.date_range,
                )
                
                # Generate helpful suggestions
                suggestions = []
                if spec.sport:
                    suggestions.append(f"Try searching for {spec.sport} highlights from a different time period")
                if spec.date_range:
                    suggestions.append("Try a broader date range or remove the date filter")
                suggestions.append("Try a more general query (e.g., 'NFL highlights' instead of specific teams)")
                suggestions.append("Check if the sport/league name is spelled correctly")
                
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=json.dumps({
                        "error_code": "NO_VIDEOS_FOUND",
                        "message": "No videos found matching your request.",
                        "detail": "We couldn't find any videos that match your search criteria. Try adjusting your query.",
                        "suggestions": suggestions,
                        "query_text": request.query_text,
                    }),
                    headers={"Content-Type": "application/json"},
                )
        except ValueError as e:
            error_msg = str(e)
            log.error("highlight_playlist_youtube_search_failed", error=error_msg, query_text=request.query_text)
            
            # Handle rate limit errors
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=json.dumps({
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "We're experiencing high demand. Please try again in a few minutes.",
                        "detail": "The YouTube API has rate-limited our requests. Your query has been saved and you can try again shortly.",
                        "retry_after": 60,
                    }),
                    headers={"Content-Type": "application/json"},
                )
            
            # Handle quota exceeded errors
            if "quota exceeded" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=json.dumps({
                        "error_code": "QUOTA_EXCEEDED",
                        "message": "Service temporarily unavailable. Please try again later.",
                        "detail": "We've reached our daily API limit. Please try again tomorrow or use a cached playlist if available.",
                        "retry_after": 3600,
                    }),
                    headers={"Content-Type": "application/json"},
                )
            
            # Handle network errors
            if "network error" in error_msg.lower() or "connection" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=json.dumps({
                        "error_code": "NETWORK_ERROR",
                        "message": "Unable to connect to video service. Please check your internet connection and try again.",
                        "detail": error_msg,
                    }),
                    headers={"Content-Type": "application/json"},
                )
            
            # Handle access denied errors
            if "access denied" in error_msg.lower() or "invalid api key" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=json.dumps({
                        "error_code": "API_ERROR",
                        "message": "Service configuration error. Please contact support if this persists.",
                        "detail": "There was an issue with the video service configuration.",
                    }),
                    headers={"Content-Type": "application/json"},
                )
            
            # Generic YouTube API error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=json.dumps({
                    "error_code": "YOUTUBE_API_ERROR",
                    "message": "Unable to search for videos at this time. Please try again in a few moments.",
                    "detail": error_msg,
                }),
                headers={"Content-Type": "application/json"},
            )
        except Exception as e:
            log.error("highlight_playlist_unexpected_error", error=str(e), error_type=type(e).__name__, query_text=request.query_text, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=json.dumps({
                    "error_code": "UNKNOWN_ERROR",
                    "message": "An unexpected error occurred. Please try again.",
                    "detail": "If this problem persists, please contact support.",
                }),
                headers={"Content-Type": "application/json"},
            )
        
        # Build playlist from candidates
        items, explanation = build_playlist_from_candidates(
            candidates,
            spec.requested_duration_minutes,
            spec,
            search_spec,
        )
        
        # Check if playlist is too short (less than 50% of requested duration)
        if items and len(items) > 0:
            actual_duration_minutes = explanation.get("actual_duration_minutes", 0)
            if actual_duration_minutes < spec.requested_duration_minutes * 0.5:
                log.warning(
                    "highlight_playlist_short_duration",
                    query_text=request.query_text,
                    requested_minutes=spec.requested_duration_minutes,
                    actual_minutes=actual_duration_minutes,
                    videos_found=len(items),
                )
                # Add note to explanation
                explanation["coverage_notes"].append(
                    f"Note: Only found {actual_duration_minutes:.1f} minutes of content "
                    f"(requested {spec.requested_duration_minutes} minutes). "
                    f"Try a broader search or different time period for more results."
                )
        
        # Compute stale_after (metadata already extracted above)
        now = datetime.utcnow()
        stale_after = compute_stale_after(event_date, now, request.mode.value)
        
        # Create or get query
        if existing_query:
            query = existing_query
            query.last_used_at = now
            # Update metadata if it's missing (for backward compatibility)
            if query.sport is None and sport_name:
                query.sport = sport_name
            if query.league is None and league_name:
                query.league = league_name
            if query.teams is None and teams_list:
                query.teams = teams_list
            if query.event_date is None and event_date:
                query.event_date = event_date
            if query.is_playoff is None and is_playoff is not None:
                query.is_playoff = is_playoff
        else:
            query = PlaylistQuery(
                query_text=request.query_text,
                normalized_signature=normalized_signature,
                mode=request.mode,
                requested_duration_minutes=spec.requested_duration_minutes,
                version=1,
                sport=sport_name,
                league=league_name,
                teams=teams_list,
                event_date=event_date,
                is_playoff=is_playoff,
            )
            session.add(query)
            await session.flush()
        
        # Create playlist
        playlist = Playlist(
            query_id=query.id,
            items=items,
            total_duration_seconds=sum(item["duration_seconds"] for item in items),
            stale_after=stale_after,
            explanation=explanation,
        )
        session.add(playlist)
        await session.commit()
        await session.refresh(playlist)
        
        # Log cache miss with metrics
        actual_duration_minutes = playlist.total_duration_seconds / 60
        log.info(
            "highlight_playlist_cache_miss",
            playlist_id=playlist.id,
            query_id=query.id,
            cache_status="fresh",
            actual_duration_minutes=round(actual_duration_minutes, 1),
            requested_duration_minutes=spec.requested_duration_minutes,
            duration_delta_minutes=round(actual_duration_minutes - spec.requested_duration_minutes, 1),
            youtube_api_calls=youtube_api_calls,
            videos_found=len(candidates),
            videos_selected=len(items),
        )
        
        return HighlightPlanResponse(
            playlist_id=playlist.id,
            query_id=query.id,
            items=items,
            total_duration_seconds=playlist.total_duration_seconds,
            cache_status="fresh",
            explanation=explanation,
            created_at=playlist.created_at.isoformat(),
            stale_after=playlist.stale_after.isoformat() if playlist.stale_after else None,
            disclaimer="This app builds playlists using public YouTube videos. We do not host or control the content.",
        )


@router.get("/{playlist_id}", response_model=HighlightDetailResponse)
async def get_highlight_playlist(playlist_id: int) -> HighlightDetailResponse:
    """Get detailed playlist information.
    
    Includes:
    - Playlist metadata
    - List of items
    - Explanation block (how it was built, scoring, assumptions)
    """
    async with get_async_session() as session:
        stmt = select(Playlist, PlaylistQuery).join(PlaylistQuery).where(Playlist.id == playlist_id)
        result = await session.execute(stmt)
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Playlist {playlist_id} not found",
            )
        
        playlist, query = row
        
        return HighlightDetailResponse(
            playlist_id=playlist.id,
            query_id=query.id,
            query_text=query.query_text,
            items=playlist.items,
            total_duration_seconds=playlist.total_duration_seconds,
            explanation=playlist.explanation,
            created_at=playlist.created_at.isoformat(),
            stale_after=playlist.stale_after.isoformat() if playlist.stale_after else None,
            query_metadata={
                "mode": query.mode.value,
                "requested_duration_minutes": query.requested_duration_minutes,
                "version": query.version,
                "created_at": query.created_at.isoformat(),
                "last_used_at": query.last_used_at.isoformat(),
            },
            disclaimer="This app builds playlists using public YouTube videos. We do not host or control the content.",
        )


@router.get("/metrics", tags=["highlights"])
async def get_highlight_metrics(days: int = 30) -> dict[str, Any]:
    """Get metrics for highlight playlists.
    
    Returns:
        Dictionary with sports request counts, average duration, and cache hit rate
    """
    async with get_async_session() as session:
        sports_counts = await get_sports_request_counts(session, days)
        avg_duration = await get_average_playlist_duration(session, days)
        cache_stats = await get_cache_hit_rate(session, days)
        
        return {
            "period_days": days,
            "sports_request_counts": sports_counts,
            "average_playlist_duration_minutes": avg_duration,
            "cache_statistics": cache_stats,
        }


@router.get("/metrics/csv", tags=["highlights"])
async def get_highlight_metrics_csv(days: int = 30) -> str:
    """Get metrics as CSV for simple dashboard.
    
    Returns:
        CSV string with metrics data
    """
    async with get_async_session() as session:
        return await export_metrics_csv(session, days)

