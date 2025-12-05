"""Admin EDA endpoints for sports data.

These endpoints power internal exploratory analysis and will eventually
serve as the backbone modeling interface for matchup evaluation and
simulations. They are **admin-only** and are not exposed to end users.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, desc, func, select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import or_

from .. import db_models
from ..db import AsyncSession, get_db
from ..services.derived_metrics import compute_derived_metrics

router = APIRouter(prefix="/api/admin/sports/eda", tags=["sports-eda"])


class EDAFilters(BaseModel):
    """High-level filters for an EDA query.

    League-specific by design – callers must choose a single league_code.
    """

    model_config = ConfigDict(populate_by_name=True)

    league_code: str = Field(..., alias="leagueCode")
    season: int | None = Field(None, alias="season")
    start_date: date | None = Field(None, alias="startDate")
    end_date: date | None = Field(None, alias="endDate")
    team: str | None = Field(
        None,
        description="Optional team name filter (substring match against home/away team names).",
    )
    season_type: str | None = Field(
        None,
        alias="seasonType",
        description="Optional season type filter ('regular', 'playoffs', etc.).",
    )
    market_type: str | None = Field(
        None,
        alias="marketType",
        description="Optional odds market type filter ('spread', 'total', 'moneyline').",
    )
    side: str | None = Field(
        None,
        alias="side",
        description="Optional odds side filter ('home', 'away', 'over', 'under').",
    )
    closing_only: bool = Field(
        True,
        alias="closingOnly",
        description="If true, only closing lines are considered when computing derived metrics.",
    )
    include_player_stats: bool = Field(
        False,
        alias="includePlayerStats",
        description="If true, include per-player stats in the response.",
    )
    team_stat_keys: list[str] = Field(
        default_factory=list,
        alias="teamStatKeys",
        description="Subset of team stat keys to include; empty means include all.",
    )
    player_stat_keys: list[str] = Field(
        default_factory=list,
        alias="playerStatKeys",
        description="Subset of player stat keys to include; empty means include all.",
    )


class EDATeamStats(BaseModel):
    team: str
    is_home: bool
    stats: dict[str, Any]


class EDAPlayerStats(BaseModel):
    team: str
    player_name: str
    stats: dict[str, Any]


class EDATargets(BaseModel):
    """Standardized outcome targets derived from scores + odds."""

    winner: str | None = None  # "home" | "away" | "tie"
    did_home_cover: bool | None = None
    did_away_cover: bool | None = None
    total_result: str | None = None  # "over" | "under" | "push"
    moneyline_upset: bool | None = None
    margin_of_victory: float | None = None
    combined_score: float | None = None
    closing_spread_home: float | None = None
    closing_spread_away: float | None = None
    closing_total: float | None = None


class EDAGameRow(BaseModel):
    """Single game row used for EDA / modeling."""

    game_id: int
    league_code: str
    season: int
    season_type: str
    game_date: datetime
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    targets: EDATargets
    team_stats: list[EDATeamStats]
    player_stats: list[EDAPlayerStats] | None = None


class EDAQueryResponse(BaseModel):
    """Response for an EDA query."""

    rows: list[EDAGameRow]
    total: int
    next_offset: int | None


async def _get_league(session: AsyncSession, code: str) -> db_models.SportsLeague:
    stmt = select(db_models.SportsLeague).where(db_models.SportsLeague.code == code.upper())
    result = await session.execute(stmt)
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"League {code} not found")
    return league


def _apply_eda_filters(stmt: Select, league: db_models.SportsLeague, filters: EDAFilters) -> Select:
    """Apply league + game filters to a base statement."""
    stmt = stmt.where(db_models.SportsGame.league_id == league.id)

    if filters.season is not None:
        stmt = stmt.where(db_models.SportsGame.season == filters.season)

    if filters.season_type:
        stmt = stmt.where(db_models.SportsGame.season_type == filters.season_type)

    if filters.start_date:
        stmt = stmt.where(db_models.SportsGame.game_date >= datetime.combine(filters.start_date, datetime.min.time()))

    if filters.end_date:
        stmt = stmt.where(db_models.SportsGame.game_date <= datetime.combine(filters.end_date, datetime.max.time()))

    if filters.team:
        pattern = f"%{filters.team}%"
        stmt = stmt.where(
            or_(
                db_models.SportsGame.home_team.has(db_models.SportsTeam.name.ilike(pattern)),
                db_models.SportsGame.away_team.has(db_models.SportsTeam.name.ilike(pattern)),
                db_models.SportsGame.home_team.has(db_models.SportsTeam.short_name.ilike(pattern)),
                db_models.SportsGame.away_team.has(db_models.SportsTeam.short_name.ilike(pattern)),
                db_models.SportsGame.home_team.has(db_models.SportsTeam.abbreviation.ilike(pattern)),
                db_models.SportsGame.away_team.has(db_models.SportsTeam.abbreviation.ilike(pattern)),
            )
        )

    return stmt


def _filter_stats(raw: dict[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    """Return a filtered stats dict based on requested keys."""
    if not raw:
        return {}
    if not keys:
        return raw
    return {k: v for k, v in raw.items() if k in keys}


def _build_targets(metrics: dict[str, Any]) -> EDATargets:
    """Project derived_metrics dict into the standardized EDATargets model."""
    return EDATargets(
        winner=metrics.get("winner"),
        did_home_cover=metrics.get("did_home_cover"),
        did_away_cover=metrics.get("did_away_cover"),
        total_result=metrics.get("total_result"),
        moneyline_upset=metrics.get("moneyline_upset"),
        margin_of_victory=metrics.get("margin_of_victory"),
        combined_score=metrics.get("combined_score"),
        closing_spread_home=metrics.get("closing_spread_home"),
        closing_spread_away=metrics.get("closing_spread_away"),
        closing_total=metrics.get("closing_total"),
    )


@router.post("/query", response_model=EDAQueryResponse)
async def run_eda_query(
    payload: EDAFilters,
    session: AsyncSession = Depends(get_db),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> EDAQueryResponse:
    """Run an EDA query for a single league.

    This endpoint is intentionally generic:
    - League-specific (no cross-league queries).
    - Returns per-game rows with standardized outcome targets and
      optional team/player stats restricted to requested keys.
    - Designed for internal tools and modeling pipelines – not for
      direct end-user consumption.
    """
    league = await _get_league(session, payload.league_code)

    base_stmt: Select = select(db_models.SportsGame).options(
        selectinload(db_models.SportsGame.league),
        selectinload(db_models.SportsGame.home_team),
        selectinload(db_models.SportsGame.away_team),
        selectinload(db_models.SportsGame.team_boxscores),
        selectinload(db_models.SportsGame.player_boxscores),
        selectinload(db_models.SportsGame.odds),
    )

    base_stmt = _apply_eda_filters(base_stmt, league, payload)

    stmt = base_stmt.order_by(desc(db_models.SportsGame.game_date)).offset(offset).limit(limit)
    results = await session.execute(stmt)
    games: list[db_models.SportsGame] = results.scalars().unique().all()

    # Separate count query for pagination
    count_stmt: Select = select(func.count(db_models.SportsGame.id))
    count_stmt = _apply_eda_filters(count_stmt, league, payload)
    total = (await session.execute(count_stmt)).scalar_one()

    rows: list[EDAGameRow] = []

    for game in games:
        # Optionally filter odds by market_type/side/closing flag before computing metrics
        odds = game.odds
        if payload.market_type:
            odds = [o for o in odds if o.market_type == payload.market_type]
        if payload.side:
            odds = [o for o in odds if (o.side or "").lower() == payload.side.lower()]
        if payload.closing_only:
            odds = [o for o in odds if o.is_closing_line]

        metrics = compute_derived_metrics(game, odds)
        targets = _build_targets(metrics)

        team_stats: list[EDATeamStats] = []
        for box in game.team_boxscores:
            # League isolation already enforced; just filter stats
            team_name = box.team.name if box.team else "Unknown"
            filtered = _filter_stats(box.stats or {}, payload.team_stat_keys)
            team_stats.append(
                EDATeamStats(
                    team=team_name,
                    is_home=box.is_home,
                    stats=filtered,
                )
            )

        player_stats: list[EDAPlayerStats] | None = None
        if payload.include_player_stats:
            player_stats = []
            for pb in game.player_boxscores:
                team_name = pb.team.name if pb.team else "Unknown"
                filtered = _filter_stats(pb.stats or {}, payload.player_stat_keys)
                if not filtered:
                    continue
                player_stats.append(
                    EDAPlayerStats(
                        team=team_name,
                        player_name=pb.player_name,
                        stats=filtered,
                    )
                )

        row = EDAGameRow(
            game_id=game.id,
            league_code=league.code,
            season=game.season,
            season_type=game.season_type,
            game_date=game.game_date,
            home_team=game.home_team.name if game.home_team else "Unknown",
            away_team=game.away_team.name if game.away_team else "Unknown",
            home_score=game.home_score,
            away_score=game.away_score,
            targets=targets,
            team_stats=team_stats,
            player_stats=player_stats,
        )
        rows.append(row)

    next_offset = offset + limit if offset + limit < total else None
    return EDAQueryResponse(rows=rows, total=total, next_offset=next_offset)


class AvailableStatKeysResponse(BaseModel):
    """Response with available stat keys for a league."""

    league_code: str
    team_stat_keys: list[str]
    player_stat_keys: list[str]


@router.get("/stat-keys/{league_code}", response_model=AvailableStatKeysResponse)
async def get_available_stat_keys(
    league_code: str,
    session: AsyncSession = Depends(get_db),
) -> AvailableStatKeysResponse:
    """Get available team and player stat keys for a given league.

    Extracts distinct keys from the JSONB stats columns in the database
    for use in the EDA UI multi-select dropdowns.
    """
    league = await _get_league(session, league_code)

    # Get distinct team stat keys using jsonb_object_keys
    team_keys_query = text("""
        SELECT DISTINCT key
        FROM sports_team_boxscores tb
        JOIN sports_games g ON tb.game_id = g.id
        CROSS JOIN LATERAL jsonb_object_keys(tb.stats) AS key
        WHERE g.league_id = :league_id
        ORDER BY key
    """)
    team_result = await session.execute(team_keys_query, {"league_id": league.id})
    team_stat_keys = [row[0] for row in team_result.fetchall()]

    # Get distinct player stat keys using jsonb_object_keys
    player_keys_query = text("""
        SELECT DISTINCT key
        FROM sports_player_boxscores pb
        JOIN sports_games g ON pb.game_id = g.id
        CROSS JOIN LATERAL jsonb_object_keys(pb.stats) AS key
        WHERE g.league_id = :league_id
        ORDER BY key
    """)
    player_result = await session.execute(player_keys_query, {"league_id": league.id})
    player_stat_keys = [row[0] for row in player_result.fetchall()]

    return AvailableStatKeysResponse(
        league_code=league.code,
        team_stat_keys=team_stat_keys,
        player_stat_keys=player_stat_keys,
    )


