"""SQLAlchemy models for dock108 theory engine persistence."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
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


class StrategyStatus(str, Enum):
    """Strategy status levels."""

    draft = "draft"
    saved = "saved"


class Strategy(Base):
    """Crypto strategy interpretations and specifications."""

    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID as string
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    idea_text: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    backtest_blueprint: Mapped[dict] = mapped_column(JSONB, nullable=False)
    diagnostics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    alerts: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[StrategyStatus] = mapped_column(String(20), default=StrategyStatus.draft, nullable=False, index=True)
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    backtests: Mapped[list[Backtest]] = relationship("Backtest", back_populates="strategy", cascade="all, delete-orphan")
    alert_events: Mapped[list[Alert]] = relationship("Alert", back_populates="strategy", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_strategies_user_created", "user_id", "created_at"), Index("idx_strategies_status", "status"))


class Backtest(Base):
    """Backtest results for strategies."""

    __tablename__ = "backtests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID as string
    strategy_id: Mapped[str] = mapped_column(String(36), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    results_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    strategy: Mapped[Strategy] = relationship("Strategy", back_populates="backtests")

    __table_args__ = (Index("idx_backtests_strategy_created", "strategy_id", "created_at"),)


class Alert(Base):
    """Alert events triggered for strategies."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID as string
    strategy_id: Mapped[str] = mapped_column(String(36), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    details_json: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)

    # Relationships
    strategy: Mapped[Strategy] = relationship("Strategy", back_populates="alert_events")

    __table_args__ = (Index("idx_alerts_strategy_triggered", "strategy_id", "triggered_at"),)


# ============================================================================
# Sports Betting Data Models
# ============================================================================


class SportsLeague(Base):
    """Sports leagues (NFL, NCAAF, NBA, NCAAB, MLB, NHL)."""

    __tablename__ = "sports_leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)  # e.g., "NFL", "NCAAF"
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "National Football League"
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # "pro" or "college"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    teams: Mapped[list["SportsTeam"]] = relationship("SportsTeam", back_populates="league", cascade="all, delete-orphan")
    games: Mapped[list["SportsGame"]] = relationship("SportsGame", back_populates="league", cascade="all, delete-orphan")
    scrape_runs: Mapped[list["SportsScrapeRun"]] = relationship("SportsScrapeRun", back_populates="league")


class SportsTeam(Base):
    """Sports teams with external provider mappings."""

    __tablename__ = "sports_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    external_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Primary provider ID
    name: Mapped[str] = mapped_column(String(200), nullable=False)  # Full name: "Rutgers Scarlet Knights"
    short_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Display name: "Rutgers"
    abbreviation: Mapped[str] = mapped_column(String(20), nullable=False)  # "LAL", "RUT"
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "Los Angeles"
    external_codes: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)  # {provider: id}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    league: Mapped[SportsLeague] = relationship("SportsLeague", back_populates="teams")
    home_games: Mapped[list["SportsGame"]] = relationship("SportsGame", foreign_keys="[SportsGame.home_team_id]", back_populates="home_team")
    away_games: Mapped[list["SportsGame"]] = relationship("SportsGame", foreign_keys="[SportsGame.away_team_id]", back_populates="away_team")

    __table_args__ = (
        Index("idx_sports_teams_league_name", "league_id", "name", unique=True),
    )


class GameStatus(str, Enum):
    """Game status values."""

    scheduled = "scheduled"
    completed = "completed"
    postponed = "postponed"
    canceled = "canceled"


class SportsGame(Base):
    """Individual games with unique constraints to prevent duplicates."""

    __tablename__ = "sports_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., 2023
    season_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "regular", "playoffs", "tournament", "bowl"
    game_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[GameStatus] = mapped_column(String(20), default=GameStatus.scheduled, nullable=False, index=True)
    source_game_key: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    scrape_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_ids: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)  # {provider: game_id}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    league: Mapped[SportsLeague] = relationship("SportsLeague", back_populates="games")
    home_team: Mapped[SportsTeam] = relationship("SportsTeam", foreign_keys=[home_team_id], back_populates="home_games")
    away_team: Mapped[SportsTeam] = relationship("SportsTeam", foreign_keys=[away_team_id], back_populates="away_games")
    team_boxscores: Mapped[list["SportsTeamBoxscore"]] = relationship("SportsTeamBoxscore", back_populates="game", cascade="all, delete-orphan")
    player_boxscores: Mapped[list["SportsPlayerBoxscore"]] = relationship("SportsPlayerBoxscore", back_populates="game", cascade="all, delete-orphan")
    odds: Mapped[list["SportsGameOdds"]] = relationship("SportsGameOdds", back_populates="game", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("league_id", "season", "game_date", "home_team_id", "away_team_id", name="uq_game_identity"),
        Index("idx_games_league_season_date", "league_id", "season", "game_date"),
        Index("idx_games_teams", "home_team_id", "away_team_id"),
    )


class SportsTeamBoxscore(Base):
    """Team-level boxscore data stored as JSONB for flexibility across sports."""

    __tablename__ = "sports_team_boxscores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_games.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    game: Mapped[SportsGame] = relationship("SportsGame", back_populates="team_boxscores")
    team: Mapped[SportsTeam] = relationship("SportsTeam")

    __table_args__ = (
        UniqueConstraint("game_id", "team_id", name="uq_team_boxscore_game_team"),
    )


class SportsPlayerBoxscore(Base):
    """Player-level boxscores stored as JSONB for flexibility across sports."""

    __tablename__ = "sports_player_boxscores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_games.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    player_external_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    player_name: Mapped[str] = mapped_column(String(200), nullable=False)
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    game: Mapped[SportsGame] = relationship("SportsGame", back_populates="player_boxscores")
    team: Mapped[SportsTeam] = relationship("SportsTeam")

    __table_args__ = (
        UniqueConstraint("game_id", "team_id", "player_external_ref", name="uq_player_boxscore_identity"),
    )


class SportsGameOdds(Base):
    """Odds data for games (multiple books/markets per game)."""

    __tablename__ = "sports_game_odds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_games.id", ondelete="CASCADE"), nullable=False, index=True)
    book: Mapped[str] = mapped_column(String(50), nullable=False)  # "draftkings", "fanduel", "pinnacle"
    market_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "spread", "total", "moneyline"
    side: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "home", "away", "over", "under"
    line: Mapped[float | None] = mapped_column(nullable=True)  # Spread points / total points
    price: Mapped[float | None] = mapped_column(nullable=True)  # American odds stored as float
    is_closing_line: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    game: Mapped[SportsGame] = relationship("SportsGame", back_populates="odds")

    __table_args__ = (
        Index(
            "uq_sports_game_odds_identity",
            "game_id",
            "book",
            "market_type",
            "is_closing_line",
            unique=True,
        ),
    )


class SportsScrapeRun(Base):
    """Tracks ingestion/scrape job runs."""

    __tablename__ = "sports_scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scraper_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "boxscore", "odds", etc.
    league_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    requested_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Celery/Bull job identifier
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    league: Mapped[SportsLeague] = relationship("SportsLeague", back_populates="scrape_runs")

    __table_args__ = (
        Index("idx_scrape_runs_league_status", "league_id", "status"),
        Index("idx_scrape_runs_created", "created_at"),
    )
