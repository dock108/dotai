"""Schema for sports highlight playlist requests."""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class Sport(str, Enum):
    """Supported sports."""

    NFL = "NFL"
    NBA = "NBA"
    MLB = "MLB"
    NHL = "NHL"
    NCAAF = "NCAAF"
    NCAAB = "NCAAB"
    PGA = "PGA"
    F1 = "F1"
    SOCCER = "SOCCER"
    TENNIS = "TENNIS"
    OTHER = "OTHER"  # For ambiguous or unspecified sports


class LoopMode(str, Enum):
    """Playlist loop modes."""

    single_playlist = "single_playlist"  # One continuous playlist
    loop_1h = "loop_1h"  # Loop every hour
    loop_full_day = "loop_full_day"  # Loop for full day (24 hours)


class ContentMix(BaseModel):
    """Content type mix for playlist."""

    highlights: float = Field(default=0.6, ge=0.0, le=1.0, description="Proportion of highlights")
    bloopers: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of bloopers")
    top_plays: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of top plays")
    condensed: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of condensed games")
    full_game: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of full games")
    upsets: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of upset highlights")

    def model_post_init(self, __context) -> None:
        """Validate that proportions sum to <= 1.0."""
        total = (
            self.highlights
            + self.bloopers
            + self.top_plays
            + self.condensed
            + self.full_game
            + self.upsets
        )
        if total > 1.0:
            raise ValueError(f"Content mix proportions sum to {total}, must be <= 1.0")


class DateRange(BaseModel):
    """Date range for sports events."""

    start_date: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="End date (YYYY-MM-DD)")
    single_date: str | None = Field(default=None, description="Single date (YYYY-MM-DD)")
    week: str | None = Field(default=None, description="Week identifier (e.g., 'Week 12', 'Week 5')")
    season: str | None = Field(default=None, description="Season (e.g., '2024', '2023-2024')")

    def model_post_init(self, __context) -> None:
        """Validate date range."""
        if self.single_date and (self.start_date or self.end_date):
            raise ValueError("Cannot specify both single_date and date range")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")


class HighlightRequestSpec(BaseModel):
    """Structured specification for sports highlight playlist request."""

    sport: Annotated[Sport, Field(description="Primary sport")]
    leagues: list[str] = Field(default_factory=list, description="Specific leagues (e.g., ['NFL', 'AFC'])")
    teams: list[str] = Field(default_factory=list, description="Specific teams (e.g., ['Kansas City Chiefs', 'Buffalo Bills'])")
    date_range: DateRange | None = Field(default=None, description="Date range for events")
    content_mix: ContentMix = Field(default_factory=ContentMix, description="Content type mix")
    requested_duration_minutes: int = Field(ge=5, le=1440, description="Requested playlist duration in minutes (5-1440)")
    loop_mode: LoopMode = Field(default=LoopMode.single_playlist, description="Playlist loop mode")
    exclusions: list[str] = Field(default_factory=list, description="Exclusions (e.g., ['no Jets', 'no Super Bowl replays'])")
    nsfw_filter: bool = Field(default=True, description="Enable NSFW filtering")
    language: str = Field(default="en", description="Language code")
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made during parsing (e.g., ['Assumed NFL for ambiguous sport', 'Interpreted full work day as 8 hours'])",
    )


class HighlightRequestParseResult(BaseModel):
    """Result of parsing user text into structured spec."""

    spec: HighlightRequestSpec
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in parsing (0-1)")
    needs_clarification: bool = Field(default=False, description="Whether clarification is needed")
    clarification_questions: list[str] = Field(
        default_factory=list, description="Questions to ask user for clarification"
    )

