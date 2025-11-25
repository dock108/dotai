"""Admin endpoints for sports data ingestion."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import selectinload

from sqlalchemy.sql import or_

from .. import db_models
from ..celery_client import get_celery_app
from ..db import AsyncSession, get_db
from ..services.derived_metrics import compute_derived_metrics

router = APIRouter(prefix="/api/admin/sports", tags=["sports-data"])


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
    league_code: str
    game_date: datetime
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


class TeamStat(BaseModel):
    team: str
    is_home: bool
    stats: dict[str, Any]
    source: str | None = None
    updated_at: datetime | None = None


class PlayerStat(BaseModel):
    team: str
    player_name: str
    minutes: float | None = None
    points: int | None = None
    rebounds: int | None = None
    assists: int | None = None
    yards: int | None = None
    touchdowns: int | None = None
    raw_stats: dict[str, Any] = Field(default_factory=dict)


class OddsEntry(BaseModel):
    book: str
    market_type: str
    side: str | None
    line: float | None
    price: float | None
    is_closing_line: bool
    observed_at: datetime | None


class GameMeta(BaseModel):
    id: int
    league_code: str
    season: int
    season_type: str | None
    game_date: datetime
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    status: str
    scrape_version: int | None
    last_scraped_at: datetime | None
    has_boxscore: bool
    has_player_stats: bool
    has_odds: bool


class GameDetailResponse(BaseModel):
    game: GameMeta
    team_stats: list[TeamStat]
    player_stats: list[PlayerStat]
    odds: list[OddsEntry]
    derived_metrics: dict[str, Any]
    raw_payloads: dict[str, Any]


class JobResponse(BaseModel):
    run_id: int
    job_id: str | None
    message: str


async def _get_league(session: AsyncSession, code: str) -> db_models.SportsLeague:
    stmt = select(db_models.SportsLeague).where(db_models.SportsLeague.code == code.upper())
    result = await session.execute(stmt)
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"League {code} not found")
    return league


def _serialize_run(run: db_models.SportsScrapeRun, league_code: str) -> ScrapeRunResponse:
    return ScrapeRunResponse(
        id=run.id,
        league_code=league_code,
        status=run.status,
        scraper_type=run.scraper_type,
        season=run.season,
        start_date=run.start_date.date() if run.start_date else None,
        end_date=run.end_date.date() if run.end_date else None,
        summary=run.summary,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        requested_by=run.requested_by,
        config=run.config,
    )


@router.post("/scraper/runs", response_model=ScrapeRunResponse)
async def create_scrape_run(payload: ScrapeRunCreateRequest, session: AsyncSession = Depends(get_db)) -> ScrapeRunResponse:
    league = await _get_league(session, payload.config.league_code)

    def _to_datetime(value: date | None) -> datetime | None:
        if not value:
            return None
        return datetime.combine(value, datetime.min.time())

    config_dict = payload.config.model_dump(by_alias=False)
    if config_dict.get("start_date") and isinstance(config_dict["start_date"], date):
        config_dict["start_date"] = config_dict["start_date"].isoformat()
    if config_dict.get("end_date") and isinstance(config_dict["end_date"], date):
        config_dict["end_date"] = config_dict["end_date"].isoformat()
    
    run = db_models.SportsScrapeRun(
        scraper_type=payload.config.scraper_type,
        league_id=league.id,
        season=payload.config.season,
        season_type=payload.config.season_type,
        start_date=_to_datetime(payload.config.start_date),
        end_date=_to_datetime(payload.config.end_date),
        status="pending",
        requested_by=payload.requested_by,
        config=config_dict,
    )
    session.add(run)
    await session.flush()

    worker_payload = payload.config.to_worker_payload()
    try:
        celery_app = get_celery_app()
        async_result = celery_app.send_task(
            "run_scrape_job",
            args=[run.id, worker_payload],
            queue="bets-scraper",
            routing_key="bets-scraper",
        )
        run.job_id = async_result.id
    except Exception as exc:  # pragma: no cover
        from ..logging_config import get_logger

        logger = get_logger(__name__)
        logger.error("failed_to_enqueue_scrape", error=str(exc), exc_info=True)
        run.status = "error"
        run.error_details = f"Failed to enqueue scrape: {exc}"
        raise HTTPException(status_code=500, detail="Failed to enqueue scrape job") from exc

    return _serialize_run(run, league.code)


@router.get("/scraper/runs", response_model=list[ScrapeRunResponse])
async def list_scrape_runs(
    league: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_db),
) -> list[ScrapeRunResponse]:
    stmt: Select[tuple[db_models.SportsScrapeRun]] = select(db_models.SportsScrapeRun).order_by(desc(db_models.SportsScrapeRun.created_at)).limit(limit)
    if league:
        league_obj = await _get_league(session, league)
        stmt = stmt.where(db_models.SportsScrapeRun.league_id == league_obj.id)
    if status_filter:
        stmt = stmt.where(db_models.SportsScrapeRun.status == status_filter)

    results = await session.execute(stmt)
    runs = results.scalars().all()

    league_map: dict[int, str] = {}
    if runs:
        stmt_leagues = select(db_models.SportsLeague.id, db_models.SportsLeague.code).where(
            db_models.SportsLeague.id.in_({run.league_id for run in runs})
        )
        league_rows = await session.execute(stmt_leagues)
        league_map = {row.id: row.code for row in league_rows}

    return [_serialize_run(run, league_map.get(run.league_id, "UNKNOWN")) for run in runs]


@router.get("/scraper/runs/{run_id}", response_model=ScrapeRunResponse)
async def fetch_run(run_id: int, session: AsyncSession = Depends(get_db)) -> ScrapeRunResponse:
    result = await session.execute(
        select(db_models.SportsScrapeRun)
        .options(selectinload(db_models.SportsScrapeRun.league))
        .where(db_models.SportsScrapeRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    league_code = run.league.code if run.league else "UNKNOWN"
    return _serialize_run(run, league_code)


def _apply_game_filters(
    stmt: Select[tuple[db_models.SportsGame]],
    leagues: Sequence[str] | None,
    season: int | None,
    team: str | None,
    start_date: date | None,
    end_date: date | None,
    missing_boxscore: bool,
    missing_player_stats: bool,
    missing_odds: bool,
    missing_any: bool,
) -> Select[tuple[db_models.SportsGame]]:
    if leagues:
        league_codes = [code.upper() for code in leagues]
        stmt = stmt.where(db_models.SportsGame.league.has(db_models.SportsLeague.code.in_(league_codes)))

    if season is not None:
        stmt = stmt.where(db_models.SportsGame.season == season)

    if team:
        pattern = f"%{team}%"
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

    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        stmt = stmt.where(db_models.SportsGame.game_date >= start_dt)

    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        stmt = stmt.where(db_models.SportsGame.game_date <= end_dt)

    if missing_boxscore:
        stmt = stmt.where(~db_models.SportsGame.team_boxscores.any())
    if missing_player_stats:
        stmt = stmt.where(~db_models.SportsGame.player_boxscores.any())
    if missing_odds:
        stmt = stmt.where(~db_models.SportsGame.odds.any())
    if missing_any:
        stmt = stmt.where(
            or_(
                ~db_models.SportsGame.team_boxscores.any(),
                ~db_models.SportsGame.player_boxscores.any(),
                ~db_models.SportsGame.odds.any(),
            )
        )
    return stmt


def _summarize_game(game: db_models.SportsGame) -> GameSummary:
    has_boxscore = bool(game.team_boxscores)
    has_player_stats = bool(game.player_boxscores)
    has_odds = bool(game.odds)
    season_type = getattr(game, "season_type", None)
    return GameSummary(
        id=game.id,
        league_code=game.league.code if game.league else "UNKNOWN",
        game_date=game.game_date,
        home_team=game.home_team.name if game.home_team else "Unknown",
        away_team=game.away_team.name if game.away_team else "Unknown",
        home_score=game.home_score,
        away_score=game.away_score,
        has_boxscore=has_boxscore,
        has_player_stats=has_player_stats,
        has_odds=has_odds,
        has_required_data=has_boxscore and has_odds,
        scrape_version=getattr(game, "scrape_version", None),
        last_scraped_at=game.last_scraped_at,
    )


@router.get("/games", response_model=GameListResponse)
async def list_games(
    session: AsyncSession = Depends(get_db),
    league: list[str] | None = Query(None),
    season: int | None = Query(None),
    team: str | None = Query(None),
    startDate: date | None = Query(None, alias="startDate"),
    endDate: date | None = Query(None, alias="endDate"),
    missingBoxscore: bool = Query(False, alias="missingBoxscore"),
    missingPlayerStats: bool = Query(False, alias="missingPlayerStats"),
    missingOdds: bool = Query(False, alias="missingOdds"),
    missingAny: bool = Query(False, alias="missingAny"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> GameListResponse:
    base_stmt = select(db_models.SportsGame).options(
        selectinload(db_models.SportsGame.league),
        selectinload(db_models.SportsGame.home_team),
        selectinload(db_models.SportsGame.away_team),
        selectinload(db_models.SportsGame.team_boxscores),
        selectinload(db_models.SportsGame.player_boxscores),
        selectinload(db_models.SportsGame.odds),
    )

    base_stmt = _apply_game_filters(
        base_stmt,
        leagues=league,
        season=season,
        team=team,
        start_date=startDate,
        end_date=endDate,
        missing_boxscore=missingBoxscore,
        missing_player_stats=missingPlayerStats,
        missing_odds=missingOdds,
        missing_any=missingAny,
    )

    stmt = base_stmt.order_by(desc(db_models.SportsGame.game_date)).offset(offset).limit(limit)
    results = await session.execute(stmt)
    games = results.scalars().unique().all()

    count_stmt = select(func.count(db_models.SportsGame.id))
    count_stmt = _apply_game_filters(
        count_stmt,
        leagues=league,
        season=season,
        team=team,
        start_date=startDate,
        end_date=endDate,
        missing_boxscore=missingBoxscore,
        missing_player_stats=missingPlayerStats,
        missing_odds=missingOdds,
        missing_any=missingAny,
    )
    total = (await session.execute(count_stmt)).scalar_one()

    next_offset = offset + limit if offset + limit < total else None
    summaries = [_summarize_game(game) for game in games]

    return GameListResponse(games=summaries, total=total, next_offset=next_offset)


def _serialize_team_stat(box: db_models.SportsTeamBoxscore) -> TeamStat:
    stats = {
        "points": box.points,
        "rebounds": box.rebounds,
        "assists": box.assists,
        "turnovers": box.turnovers,
        "passing_yards": box.passing_yards,
        "rushing_yards": box.rushing_yards,
        "receiving_yards": box.receiving_yards,
        "hits": box.hits,
        "runs": box.runs,
        "errors": box.errors,
        "shots_on_goal": box.shots_on_goal,
        "penalty_minutes": box.penalty_minutes,
    }
    stats = {k: v for k, v in stats.items() if v is not None}
    if box.raw_stats_json:
        stats["raw"] = box.raw_stats_json
    return TeamStat(
        team=box.team.name if box.team else "Unknown",
        is_home=box.is_home,
        stats=stats,
        source=box.source,
        updated_at=box.updated_at,
    )


def _serialize_player_stat(player: db_models.SportsPlayerBoxscore) -> PlayerStat:
    return PlayerStat(
        team=player.team.name if player.team else "Unknown",
        player_name=player.player_name,
        minutes=player.minutes,
        points=player.points,
        rebounds=player.rebounds,
        assists=player.assists,
        yards=player.yards,
        touchdowns=player.touchdowns,
        raw_stats=player.raw_stats_json or {},
    )


@router.get("/games/{game_id}", response_model=GameDetailResponse)
async def get_game(game_id: int, session: AsyncSession = Depends(get_db)) -> GameDetailResponse:
    result = await session.execute(
        select(db_models.SportsGame)
        .options(
            selectinload(db_models.SportsGame.league),
            selectinload(db_models.SportsGame.home_team),
            selectinload(db_models.SportsGame.away_team),
            selectinload(db_models.SportsGame.team_boxscores).selectinload(db_models.SportsTeamBoxscore.team),
            selectinload(db_models.SportsGame.player_boxscores).selectinload(db_models.SportsPlayerBoxscore.team),
            selectinload(db_models.SportsGame.odds),
        )
        .where(db_models.SportsGame.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    team_stats = [_serialize_team_stat(box) for box in game.team_boxscores]
    player_stats = [_serialize_player_stat(player) for player in game.player_boxscores]
    odds_entries = [
        OddsEntry(
            book=odd.book,
            market_type=odd.market_type,
            side=odd.side,
            line=odd.line,
            price=odd.price,
            is_closing_line=odd.is_closing_line,
            observed_at=odd.observed_at,
        )
        for odd in game.odds
    ]

    meta = GameMeta(
        id=game.id,
        league_code=game.league.code if game.league else "UNKNOWN",
        season=game.season,
        season_type=getattr(game, "season_type", None),
        game_date=game.game_date,
        home_team=game.home_team.name if game.home_team else "Unknown",
        away_team=game.away_team.name if game.away_team else "Unknown",
        home_score=game.home_score,
        away_score=game.away_score,
        status=game.status,
        scrape_version=getattr(game, "scrape_version", None),
        last_scraped_at=game.last_scraped_at,
        has_boxscore=bool(game.team_boxscores),
        has_player_stats=bool(game.player_boxscores),
        has_odds=bool(game.odds),
    )

    derived = compute_derived_metrics(game, game.odds)
    raw_payloads = {
        "team_boxscores": [
            {
                "team": box.team.name if box.team else "Unknown",
                "raw": box.raw_stats_json,
                "source": box.source,
            }
            for box in game.team_boxscores
            if box.raw_stats_json
        ],
        "player_boxscores": [
            {
                "team": player.team.name if player.team else "Unknown",
                "player": player.player_name,
                "raw": player.raw_stats_json,
            }
            for player in game.player_boxscores
            if player.raw_stats_json
        ],
        "odds": [
            {
                "book": odd.book,
                "market_type": odd.market_type,
                "raw": odd.raw_payload,
            }
            for odd in game.odds
            if odd.raw_payload
        ],
    }

    return GameDetailResponse(
        game=meta,
        team_stats=team_stats,
        player_stats=player_stats,
        odds=odds_entries,
        derived_metrics=derived,
        raw_payloads=raw_payloads,
    )


async def _enqueue_single_game_run(
    session: AsyncSession,
    game: db_models.SportsGame,
    *,
    include_boxscores: bool,
    include_odds: bool,
    scraper_type: str,
) -> JobResponse:
    if not game.league:
        await session.refresh(game, attribute_names=["league"])
    if not game.league:
        raise HTTPException(status_code=400, detail="League missing for game")

    config = ScrapeRunConfig(
        league_code=game.league.code,
        scraper_type=scraper_type,
        season=game.season,
        season_type=getattr(game, "season_type", "regular"),
        start_date=game.game_date.date(),
        end_date=game.game_date.date(),
        include_boxscores=include_boxscores,
        include_odds=include_odds,
        rescrape_existing=True,
    )

    run = db_models.SportsScrapeRun(
        scraper_type=scraper_type,
        league_id=game.league_id,
        season=game.season,
        season_type=getattr(game, "season_type", "regular"),
        start_date=datetime.combine(game.game_date.date(), datetime.min.time()),
        end_date=datetime.combine(game.game_date.date(), datetime.min.time()),
        status="pending",
        requested_by="admin_boxscore_viewer",
        config=config.model_dump(by_alias=False),
    )
    session.add(run)
    await session.flush()

    worker_payload = config.to_worker_payload()
    celery_app = get_celery_app()
    async_result = celery_app.send_task(
        "run_scrape_job",
        args=[run.id, worker_payload],
        queue="bets-scraper",
        routing_key="bets-scraper",
    )
    run.job_id = async_result.id

    return JobResponse(run_id=run.id, job_id=async_result.id, message="Job enqueued")


@router.post("/games/{game_id}/rescrape", response_model=JobResponse)
async def rescrape_game(game_id: int, session: AsyncSession = Depends(get_db)) -> JobResponse:
    game = await session.get(db_models.SportsGame, game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return await _enqueue_single_game_run(
        session,
        game,
        include_boxscores=True,
        include_odds=False,
        scraper_type="game_rescrape",
    )


@router.post("/games/{game_id}/resync-odds", response_model=JobResponse)
async def resync_game_odds(game_id: int, session: AsyncSession = Depends(get_db)) -> JobResponse:
    game = await session.get(db_models.SportsGame, game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return await _enqueue_single_game_run(
        session,
        game,
        include_boxscores=False,
        include_odds=True,
        scraper_type="odds_resync",
    )


