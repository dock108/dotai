"""Highlights API router for sports highlight playlists."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..db import get_async_session
from ..db_models import Playlist, PlaylistMode, PlaylistQuery
from ..highlight_parser import parse_highlight_request
from ..playlist_helpers import generate_normalized_signature, PlaylistQuerySpec
from ..logging_config import get_logger
from ..watch_token import generate_watch_token, validate_watch_token
from ..metrics import (
    get_sports_request_counts,
    get_average_playlist_duration,
    get_cache_hit_rate,
    export_metrics_csv,
)
from py_core.playlist.staleness import compute_stale_after, should_refresh_playlist
from ..sports_search import SportsSearchSpec, search_youtube_sports, calculate_highlight_score
from ..description_analyzer import analyze_video_descriptions_batch, DescriptionAnalysis
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
    # Structured builder fields (optional, for guided builder UI)
    sports: list[str] | None = Field(default=None, description="Selected sports from builder")
    teams: list[str] | None = Field(default=None, description="Selected teams from builder")
    players: list[str] | None = Field(default=None, description="Selected players from builder")
    play_types: list[str] | None = Field(default=None, description="Selected play types from builder")
    date_preset: str | None = Field(default=None, description="Date preset (last2days, last7days, etc.)")
    custom_start_date: str | None = Field(default=None, description="Custom start date (YYYY-MM-DD)")
    custom_end_date: str | None = Field(default=None, description="Custom end date (YYYY-MM-DD)")
    duration_minutes: int | None = Field(default=None, description="Requested duration in minutes")
    comments: str | None = Field(default=None, description="Additional comments/instructions")


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


class WatchTokenResponse(BaseModel):
    """Response for watch token generation."""

    token: str = Field(description="JWT token for accessing playlist")
    watch_url: str = Field(description="Full watch URL path")
    expires_at: str = Field(description="ISO timestamp when token expires")


def build_highlight_spec_from_structured_input(request: HighlightPlanRequest) -> HighlightRequestSpec:
    """Build HighlightRequestSpec from structured input without AI parsing.
    
    This is used when the frontend provides structured fields (sports, teams, players, etc.)
    to avoid unnecessary OpenAI API calls.
    
    Args:
        request: Request with structured fields
    
    Returns:
        HighlightRequestSpec built from structured input
    """
    from py_core.schemas.highlight_request import Sport, ContentMix, DateRange, LoopMode
    
    # Determine sport (use first sport from list, default to OTHER if not found)
    # Map common sport names to enum values
    sport_name_mapping = {
        "GOLF": "PGA",
        "COLLEGE BASEBALL": "NCAAB",  # Approximate mapping
        "SOCCER (INTL)": "SOCCER",
        "PREMIER LEAGUE": "SOCCER",
        "MLS": "SOCCER",
        "WNBA": "NBA",  # Approximate - WNBA is part of NBA ecosystem
    }
    
    sport = Sport.OTHER
    if request.sports and len(request.sports) > 0:
        try:
            sport_value = request.sports[0].upper()
            # Check mapping first
            if sport_value in sport_name_mapping:
                sport_value = sport_name_mapping[sport_value]
            # Check if it's a valid enum value
            if sport_value in [s.value for s in Sport]:
                sport = Sport(sport_value)
        except (ValueError, AttributeError):
            pass
    
    # Build date range from preset
    date_range = None
    if request.date_preset:
        from ..utils.date_range_utils import build_date_range_from_preset
        
        date_range_obj = build_date_range_from_preset(
            request.date_preset,
            request.custom_start_date,
            request.custom_end_date,
        )
        if date_range_obj:
            date_range = DateRange(
                start_date=date_range_obj.start_date,
                end_date=date_range_obj.end_date,
                single_date=None,
                week=None,
                season=None,
            )
    
    # Default to last 7 days if no date range
    if not date_range:
        from ..utils.date_range_utils import get_default_date_range
        
        default_range = get_default_date_range()
        date_range = DateRange(
            start_date=default_range.start_date,
            end_date=default_range.end_date,
            single_date=None,
            week=None,
            season=None,
        )
    
    # Determine duration (default to 90 minutes if not specified)
    duration = request.duration_minutes or 90
    if duration < 60:
        duration = 60
    elif duration > 600:
        duration = 600
    
    # Build assumptions list
    assumptions = []
    if request.date_preset:
        preset_assumptions = {
            "last2days": "Defaulted to last 48 hours for recent highlights catch-up",
            "last7days": "Defaulted to last 7 days for weekly catch-up",
            "last14days": "Defaulted to last 14 days for two-week catch-up",
            "last30days": "Defaulted to last 30 days for monthly catch-up",
        }
        if request.date_preset in preset_assumptions:
            assumptions.append(preset_assumptions[request.date_preset])
    
    if not date_range or (not date_range.start_date and not date_range.end_date):
        assumptions.append("No date range specified - defaulted to last 7 days for recent highlights catch-up")
    
    # Build content mix from comments if provided (basic heuristic)
    content_mix = ContentMix()
    if request.comments:
        comments_lower = request.comments.lower()
        if "blooper" in comments_lower or "funny" in comments_lower:
            content_mix.bloopers = 0.3
            content_mix.highlights = 0.7
        elif "top play" in comments_lower or "best" in comments_lower:
            content_mix.top_plays = 0.4
            content_mix.highlights = 0.6
        else:
            content_mix.highlights = 1.0
    
    return HighlightRequestSpec(
        sport=sport,
        leagues=[],
        teams=request.teams or [],
        players=request.players or [],
        play_types=request.play_types or [],
        date_range=date_range,
        content_mix=content_mix,
        requested_duration_minutes=duration,
        loop_mode=LoopMode.single_playlist,
        exclusions=[],
        nsfw_filter=True,
        language="en",
        assumptions=assumptions,
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
        players=spec.players if spec.players else None,
        play_types=spec.play_types if spec.play_types else None,
        date_range=date_range,
        content_types=content_types,
        duration_target_minutes=10,  # Default target per video
    )


async def build_playlist_from_candidates(
    candidates: list[Any],
    requested_duration_minutes: int,
    spec: HighlightRequestSpec,
    search_spec: SportsSearchSpec,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build playlist items from video candidates with iterative filtering.
    
    Uses AI-powered description analysis to filter and backfill until playlist is full.
    
    Args:
        candidates: List of VideoCandidate objects from search (already sorted by score)
        requested_duration_minutes: Target duration
        spec: Highlight request spec
        search_spec: Sports search spec used for search
    
    Returns:
        Tuple of (playlist_items, explanation_dict)
    """
    # Get logger for this function
    from ..logging_config import get_logger
    log = get_logger(__name__)
    target_seconds = requested_duration_minutes * 60
    tolerance = target_seconds * 0.1  # 10% tolerance
    
    selected_items: list[dict[str, Any]] = []
    total_duration = 0
    coverage_notes: list[str] = []
    analyzed_count = 0
    rejected_count = 0
    
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
    
    # Build query spec for description analysis
    query_spec = {
        "sport": search_spec.sport,
        "players": search_spec.players or [],
        "play_types": search_spec.play_types or [],
        "teams": search_spec.teams or [],
        "date_range": search_spec.date_range,
    }
    
    # Iterative filtering: process candidates in batches
    batch_size = 20  # Analyze 20 videos at a time
    candidate_index = 0
    analyzed_videos = []  # Track which videos we've analyzed
    
    while candidate_index < len(candidates) and total_duration < target_seconds + tolerance:
        # Take next batch of candidates
        batch = candidates[candidate_index:candidate_index + batch_size]
        if not batch:
            break
        
        # Prepare videos for analysis
        videos_to_analyze = []
        for candidate in batch:
            videos_to_analyze.append({
                "candidate": candidate,
                "title": candidate.title,
                "description": candidate.description,
                "channel_title": candidate.channel_title,
            })
        
        # Analyze descriptions in batch
        try:
            analysis_results = await analyze_video_descriptions_batch(
                videos_to_analyze,
                query_spec,
                batch_size=15,  # Process 15 at a time within the batch
            )
            # Log successful analysis
            analyzed_in_batch = len([r for r in analysis_results if r[1].is_relevant and r[1].is_high_quality])
            log.debug(
                "video_description_analysis_batch_completed",
                batch_size=len(videos_to_analyze),
                analyzed_count=len(analysis_results),
                relevant_count=analyzed_in_batch,
            )
        except Exception as e:
            # Log the failure with details
            log.warning(
                "video_description_analysis_failed",
                error=str(e),
                error_type=type(e).__name__,
                batch_size=len(videos_to_analyze),
                fallback_to_basic_filtering=True,
                exc_info=True,
            )
            # If analysis fails, fall back to basic filtering
            coverage_notes.append(f"Description analysis failed: {str(e)}, using basic filtering")
            analysis_results = []
            for video in videos_to_analyze:
                # Conservative: assume not analyzed
                from ..description_analyzer import DescriptionAnalysis
                analysis = DescriptionAnalysis(
                    is_relevant=True,  # Assume relevant if analysis fails
                    is_high_quality=True,
                    confidence=0.5,
                    extracted_metadata={},
                )
                analysis_results.append((video, analysis))
        
        # Filter and add videos that pass analysis
        for (video_dict, analysis) in analysis_results:
            candidate = video_dict["candidate"]
            analyzed_count += 1
            
            # Quality thresholds - stricter for play-type specific queries
            min_relevance = 0.7
            min_quality = 0.6
            
            # If play types are specified, require higher relevance (play types must be the focus)
            if search_spec.play_types:
                min_relevance = 0.8  # Stricter threshold for play-type queries
            
            # Check if video passes analysis
            if not analysis.is_relevant or analysis.confidence < min_relevance:
                rejected_count += 1
                continue
            
            # For play-type queries, check if rejection reason mentions it's not play-type focused
            if search_spec.play_types and analysis.rejection_reason:
                rejection_lower = analysis.rejection_reason.lower()
                if any(term in rejection_lower for term in ["general", "game highlights", "not focused", "not primarily"]):
                    rejected_count += 1
                    continue
            
            # For recent date ranges, check if rejection reason mentions it's too old or season recap
            if spec.date_range and spec.date_range.start_date:
                try:
                    start_dt = datetime.fromisoformat(spec.date_range.start_date)
                    days_ago = (datetime.now() - start_dt).days
                    if days_ago <= 30 and analysis.rejection_reason:
                        rejection_lower = analysis.rejection_reason.lower()
                        if any(term in rejection_lower for term in ["season recap", "best of season", "too old", "outside date range", "historical"]):
                            rejected_count += 1
                            continue
                except (ValueError, AttributeError):
                    pass
            
            if not analysis.is_high_quality or analysis.confidence < min_quality:
                # Lower quality but might still be acceptable if no better options
                # Only reject if we have many candidates left
                if candidate_index + len(batch) < len(candidates) * 0.5:
                    rejected_count += 1
                    continue
            
            # Video passed analysis - add to playlist
            scores = calculate_highlight_score(
                candidate, event_date, sport_name, search_spec.players, search_spec.play_types
            )
            
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
                "analysis_confidence": analysis.confidence,
                "extracted_metadata": analysis.extracted_metadata,
            }
            
            selected_items.append(item)
            total_duration += candidate.duration_seconds
            
            # Stop if we've reached target
            if total_duration >= target_seconds + tolerance:
                break
        
        # Move to next batch
        candidate_index += batch_size
    
    # Check if we reached target
    if total_duration < target_seconds - tolerance:
        coverage_notes.append(
            f"Only found {round(total_duration / 60, 1)} minutes of high-quality content (target: {requested_duration_minutes} minutes). "
            f"Analyzed {analyzed_count} videos, rejected {rejected_count} low-quality/irrelevant videos."
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
        "analyzed_count": analyzed_count,
        "rejected_count": rejected_count,
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
    
    # Step 2: Parse request (AI or structured input)
    try:
        # Check if we have structured input (from guided builder UI)
        has_structured_input = bool(
            request.sports
            or request.teams
            or request.players
            or request.play_types
            or request.date_preset
            or request.duration_minutes
        )
        
        # If we have structured input, build spec directly without AI parsing
        if has_structured_input:
            log.info("highlight_playlist_using_structured_input", structured_fields={
                "sports": bool(request.sports),
                "teams": bool(request.teams),
                "players": bool(request.players),
                "play_types": bool(request.play_types),
                "date_preset": bool(request.date_preset),
                "duration": bool(request.duration_minutes),
            })
            spec = build_highlight_spec_from_structured_input(request)
        else:
            # No structured input - use AI parsing
            log.info("highlight_playlist_using_ai_parsing")
            parse_result = await parse_highlight_request(normalized_text)
            spec = parse_result.spec
            
            # If no date range specified, default to last 7 days for recent highlights focus
            if not spec.date_range or (not spec.date_range.start_date and not spec.date_range.end_date and not spec.date_range.single_date):
                from ..utils.date_range_utils import get_default_date_range
                
                spec.date_range = get_default_date_range()
                spec.assumptions.append("No date range specified - defaulted to last 7 days for recent highlights catch-up")
    except ValueError as e:
        # User-friendly parsing errors
        from ..utils.error_handlers import create_parse_error_response, create_configuration_error_response
        
        error_msg = str(e)
        if "API key" in error_msg:
            raise create_configuration_error_response()
        raise create_parse_error_response()
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
                # Check if stale (use timezone-aware datetime)
                from ..utils.datetime_utils import now_utc
                
                now = now_utc()
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
            # Log before search to track AI query generation
            log.debug("highlight_playlist_search_starting", search_spec={
                "sport": search_spec.sport,
                "has_players": bool(search_spec.players),
                "has_play_types": bool(search_spec.play_types),
                "has_teams": bool(search_spec.teams),
            })
            candidates, youtube_api_calls = await search_youtube_sports(search_spec, initial_search_limit=250)
            log.debug("highlight_playlist_search_completed", candidates_found=len(candidates), youtube_api_calls=youtube_api_calls)
            
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
            log.error(
                "highlight_playlist_youtube_search_failed",
                error=error_msg,
                error_type=type(e).__name__,
                query_text=request.query_text,
                exc_info=True,  # Include full traceback
            )
            
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
            
            # Generic YouTube API error - check if it might be a 503 case
            # If error message suggests service unavailable, return 503
            if any(term in error_msg.lower() for term in ["unavailable", "temporarily", "service", "503"]):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=json.dumps({
                        "error_code": "SERVICE_UNAVAILABLE",
                        "message": "Video service is temporarily unavailable. Please try again in a few moments.",
                        "detail": error_msg,
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
        except HTTPException:
            # Re-raise HTTPExceptions (like NO_VIDEOS_FOUND) - they're already properly formatted
            raise
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
        items, explanation = await build_playlist_from_candidates(
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
        from ..utils.datetime_utils import now_utc
        
        now = now_utc()
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
        
        # Calculate recency metrics
        date_window_days = None
        if spec.date_range and spec.date_range.start_date and spec.date_range.end_date:
            try:
                start_dt = datetime.fromisoformat(spec.date_range.start_date)
                end_dt = datetime.fromisoformat(spec.date_range.end_date)
                date_window_days = (end_dt - start_dt).days
            except (ValueError, AttributeError):
                pass
        
        # Builder usage stats
        builder_used = bool(request.sports or request.teams or request.players or request.play_types)
        builder_stats = {
            "sports_count": len(request.sports) if request.sports else 0,
            "teams_count": len(request.teams) if request.teams else 0,
            "players_count": len(request.players) if request.players else 0,
            "play_types_count": len(request.play_types) if request.play_types else 0,
            "date_preset": request.date_preset or None,
        }
        
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
            date_window_days=date_window_days,
            builder_used=builder_used,
            builder_stats=builder_stats,
            inferred_date_window=bool(spec.assumptions and any("defaulted" in a.lower() or "assumed" in a.lower() for a in spec.assumptions)),
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
        
        # Handle mode - it might be a string or an enum
        mode_value = query.mode.value if hasattr(query.mode, 'value') else str(query.mode)
        
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
                "mode": mode_value,
                "requested_duration_minutes": query.requested_duration_minutes,
                "version": query.version,
                "created_at": query.created_at.isoformat(),
                "last_used_at": query.last_used_at.isoformat(),
                "sport": query.sport,
                "league": query.league,
                "teams": query.teams,
                "event_date": query.event_date.isoformat() if query.event_date else None,
                "is_playoff": query.is_playoff,
            },
            disclaimer="This app builds playlists using public YouTube videos. We do not host or control the content.",
        )


@router.post("/{playlist_id}/watch-token", response_model=WatchTokenResponse)
async def generate_watch_token_for_playlist(playlist_id: int) -> WatchTokenResponse:
    """Generate a temporary watch token for a playlist.
    
    The token expires after 48 hours and can be used to access the playlist
    via the /api/highlights/watch/{token} endpoint.
    """
    # Verify playlist exists
    async with get_async_session() as session:
        stmt = select(Playlist).where(Playlist.id == playlist_id)
        result = await session.execute(stmt)
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=json.dumps({
                    "error_code": "NOT_FOUND",
                    "message": "Playlist not found",
                    "detail": f"Playlist {playlist_id} does not exist",
                }),
                headers={"Content-Type": "application/json"},
            )
    
    # Generate token
    token = generate_watch_token(playlist_id)
    
    # Extract expiration from token payload
    payload = validate_watch_token(token)
    expires_at = payload.get("expires_at", "") if payload else ""
    
    return WatchTokenResponse(
        token=token,
        watch_url=f"/watch/{token}",
        expires_at=expires_at,
    )


@router.get("/watch/{token}", response_model=HighlightDetailResponse)
async def get_playlist_by_watch_token(token: str) -> HighlightDetailResponse:
    """Get playlist data using a watch token.
    
    This endpoint validates the token and returns playlist data if valid.
    Returns 403 if token is expired or invalid.
    """
    # Validate token
    payload = validate_watch_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=json.dumps({
                "error_code": "TOKEN_INVALID",
                "message": "Invalid watch link.",
                "detail": "The watch link is invalid or has expired. Generate a new link from the playlist page.",
            }),
            headers={"Content-Type": "application/json"},
        )
    
    playlist_id = payload.get("playlist_id")
    if not playlist_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=json.dumps({
                "error_code": "TOKEN_INVALID",
                "message": "Invalid watch link.",
                "detail": "The watch link is malformed.",
            }),
            headers={"Content-Type": "application/json"},
        )
    
    # Check expiration explicitly (double-check)
    expires_at_str = payload.get("expires_at")
    if expires_at_str:
        from datetime import timezone as tz
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        now = datetime.now(tz.utc)
        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=json.dumps({
                    "error_code": "TOKEN_EXPIRED",
                    "message": "This watch link has expired. Generate a new link from the playlist page.",
                    "detail": f"Token expired at {expires_at_str}",
                }),
                headers={"Content-Type": "application/json"},
            )
    
    # Fetch playlist (reuse existing endpoint logic)
    async with get_async_session() as session:
        stmt = select(Playlist, PlaylistQuery).join(PlaylistQuery).where(Playlist.id == playlist_id)
        result = await session.execute(stmt)
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=json.dumps({
                    "error_code": "NOT_FOUND",
                    "message": "Playlist not found.",
                    "detail": f"Playlist {playlist_id} does not exist",
                }),
                headers={"Content-Type": "application/json"},
            )
        
        playlist, query = row
        
        # Handle mode - it might be a string or an enum
        mode_value = query.mode.value if hasattr(query.mode, 'value') else str(query.mode)
        
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
                "mode": mode_value,
                "requested_duration_minutes": query.requested_duration_minutes,
                "version": query.version,
                "created_at": query.created_at.isoformat(),
                "last_used_at": query.last_used_at.isoformat(),
                "sport": query.sport,
                "league": query.league,
                "teams": query.teams,
                "event_date": query.event_date.isoformat() if query.event_date else None,
                "is_playoff": query.is_playoff,
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

