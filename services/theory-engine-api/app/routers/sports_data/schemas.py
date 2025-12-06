"""Pydantic schemas for sports data admin API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScrapeRunConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    league_code: str = Field(..., alias="leagueCode")
    scraper_type: str = Field("boxscore_and_odds", alias="scraperType")
    season: int | None = Field(None, alias="season")
    season_type: str = Field("regular", alias="seasonType")
    start_date: date | None = Field(None, alias="startDate")
    end_date: date | None = Field(None, alias="endDate")
    include_boxscores: bool = Field(True, alias="includeBoxscores")
    include_odds: bool = Field(True, alias="includeOdds")
    include_books: list[str] | None = Field(None, alias="books")
    rescrape_existing: bool = Field(False, alias="rescrapeExisting")
    only_missing: bool = Field(False, alias="onlyMissing")
    backfill_player_stats: bool = Field(False, alias="backfillPlayerStats")
    backfill_odds: bool = Field(False, alias="backfillOdds")

    def to_worker_payload(self) -> dict[str, Any]:
        return {
            "scraper_type": self.scraper_type,
            "league_code": self.league_code,
            "season": self.season,
            "season_type": self.season_type,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "include_boxscores": self.include_boxscores,
            "include_odds": self.include_odds,
            "include_books": self.include_books,
            "rescrape_existing": self.rescrape_existing,
            "only_missing": self.only_missing,
            "backfill_player_stats": self.backfill_player_stats,
            "backfill_odds": self.backfill_odds,
        }


class ScrapeRunCreateRequest(BaseModel):
    config: ScrapeRunConfig
    requested_by: str | None = Field(None, alias="requestedBy")


class ScrapeRunResponse(BaseModel):
    id: int
    league_code: str
    status: str
    scraper_type: str
    season: int | None
    start_date: date | None
    end_date: date | None
    summary: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    requested_by: str | None
    config: dict[str, Any] | None = None


class GameSummary(BaseModel):
    id: int
    game_date: datetime
    league_code: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    has_boxscore: bool
    has_player_stats: bool
    has_odds: bool
    has_required_data: bool
    scrape_version: int | None
    last_scraped_at: datetime | None


class GameListResponse(BaseModel):
    games: list[GameSummary]
    total: int
    next_offset: int | None
    with_boxscore_count: int | None = 0
    with_player_stats_count: int | None = 0
    with_odds_count: int | None = 0


class TeamStat(BaseModel):
    team: str
    is_home: bool
    stats: dict[str, Any]


class PlayerStat(BaseModel):
    player_name: str
    team: str
    stats: dict[str, Any]


class OddsEntry(BaseModel):
    book: str
    market_type: str
    side: str | None
    line: float | None
    price: int | None
    is_closing_line: bool
    observed_at: datetime


class GameMeta(BaseModel):
    id: int
    game_date: datetime
    league_code: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    status: str
    venue: str | None
    season: int | None
    season_type: str | None


class GameDetailResponse(BaseModel):
    game: GameMeta
    team_stats: list[TeamStat]
    player_stats: list[PlayerStat]
    odds: list[OddsEntry]
    derived_metrics: dict[str, Any] | None = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class TeamSummary(BaseModel):
    id: int
    name: str
    abbreviation: str | None
    league_code: str
    game_count: int


class TeamListResponse(BaseModel):
    teams: list[TeamSummary]
    total: int


class TeamGameSummary(BaseModel):
    game_id: int
    game_date: datetime
    opponent: str
    is_home: bool
    score: int | None
    opponent_score: int | None


class TeamDetail(BaseModel):
    team: TeamSummary
    games: list[TeamGameSummary]
    total_games: int

