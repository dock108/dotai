"""Helper functions for highlights API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from py_core.schemas.highlight_request import ContentMix, DateRange, HighlightRequestSpec, LoopMode, Sport

from ...sports_search import SportsSearchSpec
from ..highlights.schemas import HighlightPlanRequest


def build_highlight_spec_from_structured_input(request: HighlightPlanRequest) -> HighlightRequestSpec:
    """Build HighlightRequestSpec from structured input without AI parsing.
    
    This is used when the frontend provides structured fields (sports, teams, players, etc.)
    to avoid unnecessary OpenAI API calls.
    """
    sport_name_mapping = {
        "GOLF": "PGA",
        "COLLEGE BASEBALL": "NCAAB",
        "SOCCER (INTL)": "SOCCER",
        "PREMIER LEAGUE": "SOCCER",
        "MLS": "SOCCER",
        "WNBA": "NBA",
    }
    
    sport = Sport.OTHER
    if request.sports and len(request.sports) > 0:
        try:
            sport_value = request.sports[0].upper()
            if sport_value in sport_name_mapping:
                sport_value = sport_name_mapping[sport_value]
            if sport_value in [s.value for s in Sport]:
                sport = Sport(sport_value)
        except (ValueError, AttributeError):
            pass
    
    date_range = None
    if request.date_preset:
        from ...utils.date_range_utils import build_date_range_from_preset
        
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
    
    if not date_range:
        from ...utils.date_range_utils import get_default_date_range
        
        default_range = get_default_date_range()
        date_range = DateRange(
            start_date=default_range.start_date,
            end_date=default_range.end_date,
            single_date=None,
            week=None,
            season=None,
        )
    
    duration = request.duration_minutes or 90
    if duration < 60:
        duration = 60
    elif duration > 600:
        duration = 600
    
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
        content_types = ["highlights"]
    
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
        duration_target_minutes=10,
    )


def validate_highlight_request(request: HighlightPlanRequest) -> list[str]:
    """Validate highlight request and return list of validation errors."""
    errors = []
    
    if not request.query_text or len(request.query_text.strip()) < 5:
        errors.append("Query text must be at least 5 characters")
    
    if request.custom_start_date and request.custom_end_date:
        try:
            start = datetime.fromisoformat(request.custom_start_date)
            end = datetime.fromisoformat(request.custom_end_date)
            if start > end:
                errors.append("Start date must be before end date")
        except ValueError:
            errors.append("Invalid date format (expected YYYY-MM-DD)")
    
    if request.duration_minutes and (request.duration_minutes < 1 or request.duration_minutes > 600):
        errors.append("Duration must be between 1 and 600 minutes")
    
    return errors

