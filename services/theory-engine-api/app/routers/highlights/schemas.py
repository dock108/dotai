"""Pydantic schemas for highlights API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...db_models import PlaylistMode


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
    """Response containing a watch token for a playlist."""

    token: str
    expires_at: str
    playlist_id: int

