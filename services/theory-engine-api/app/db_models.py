"""SQLAlchemy models for dock108 theory engine persistence."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Any


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class UserTier(str, Enum):
    """User subscription tier levels."""

    free = "free"
    silver = "silver"
    gold = "gold"
    unlimited = "unlimited"


class CustomerAccount(Base):
    """User/customer account table.
    
    Privacy: No PII stored. Only anonymous user IDs and tier.
    """

    __tablename__ = "customer_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tier: Mapped[UserTier] = mapped_column(String(20), default=UserTier.free, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Privacy: Opt-in for using data to improve models (default: False)
    allow_model_improvement: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    theories: Mapped[list[Theory]] = relationship("Theory", back_populates="user", cascade="all, delete-orphan")


class Theory(Base):
    """Stored theory submissions.
    
    Privacy: Only raw_text and normalized_text stored. No PII extraction or storage.
    User association is optional (anonymous submissions allowed).
    """

    __tablename__ = "theories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("customer_accounts.id"), nullable=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user: Mapped[CustomerAccount | None] = relationship("CustomerAccount", back_populates="theories")
    evaluations: Mapped[list[Evaluation]] = relationship("Evaluation", back_populates="theory", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_theories_domain_created", "domain", "created_at"),)


class Evaluation(Base):
    """Evaluation results for a theory."""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    theory_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("theories.id"), nullable=False, index=True)
    verdict: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    long_term_outcome_example: Mapped[str] = mapped_column(Text, nullable=False)
    guardrail_flags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    used_models: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    theory: Mapped[Theory] = relationship("Theory", back_populates="evaluations")

    __table_args__ = (Index("idx_evaluations_theory_created", "theory_id", "created_at"),)


class ContextType(str, Enum):
    """Types of external context cached."""

    youtube = "youtube"
    odds = "odds"
    crypto_price = "crypto_price"
    stock_price = "stock_price"
    play_by_play = "play_by_play"


class ExternalContextCache(Base):
    """Cache layer for external API responses (YouTube, odds, prices, etc.)."""

    __tablename__ = "external_context_cache"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    context_type: Mapped[ContextType] = mapped_column(String(50), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 of query params
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_context_type_hash", "context_type", "key_hash", unique=True),
        Index("idx_context_expires", "expires_at"),
    )


class PlaylistMode(str, Enum):
    """Playlist generation modes."""

    sports_highlight = "sports_highlight"
    general_playlist = "general_playlist"


class PlaylistQuery(Base):
    """Stored playlist queries with normalized signatures for caching.
    
    Used for both sports highlights and general playlists.
    """

    __tablename__ = "playlist_queries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)  # Raw user input
    normalized_signature: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # Hash of structured spec (sport, leagues, teams, date_range, etc.)
    mode: Mapped[PlaylistMode] = mapped_column(String(30), nullable=False, index=True, default=PlaylistMode.general_playlist)
    requested_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Schema version for scoring/parsing changes

    # Metadata fields for future integration with betting util / theory engine
    sport: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)  # e.g., "NFL", "NBA", "MLB"
    league: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "NFL", "AFC", "Big Ten"
    teams: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)  # List of team names
    event_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)  # Date of the sports event
    is_playoff: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # Whether this is a playoff game

    # Relationships
    playlists: Mapped[list[Playlist]] = relationship("Playlist", back_populates="query", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_queries_signature_mode", "normalized_signature", "mode"),
        Index("idx_queries_created", "created_at"),
        Index("idx_queries_sport_event", "sport", "event_date"),
    )


class Playlist(Base):
    """Generated playlists with video items.
    
    Items stored as JSONB for flexibility. Staleness computed based on event recency.
    """

    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    query_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("playlist_queries.id"), nullable=False, index=True)
    items: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
    )  # List of video objects: video_id, title, channel_id, duration, source_score, freshness_score, etc.
    total_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    stale_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Computed based on event recency
    explanation: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )  # Explanation JSON: assumptions, filters_applied, ranking_factors, coverage_notes

    # Relationships
    query: Mapped[PlaylistQuery] = relationship("PlaylistQuery", back_populates="playlists")

    __table_args__ = (Index("idx_playlists_stale_after", "stale_after"), Index("idx_playlists_query_created", "query_id", "created_at"))


class Video(Base):
    """Cached video metadata (optional but useful for deduplication and analytics).
    
    Stores YouTube video information to avoid repeated API calls.
    """

    __tablename__ = "videos"

    video_id: Mapped[str] = mapped_column(String(20), primary_key=True)  # YouTube video ID
    title: Mapped[str] = mapped_column(Text, nullable=False)
    channel_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_sports_highlight: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)  # Boolean or score (0-1)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())

    __table_args__ = (Index("idx_videos_channel_published", "channel_id", "published_at"), Index("idx_videos_sports_highlight", "is_sports_highlight"))

