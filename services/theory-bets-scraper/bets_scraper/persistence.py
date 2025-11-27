"""Persistence helpers for normalized scraper payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .db import db_models
from .logging import logger
from .models import (
    GameIdentification,
    NormalizedGame,
    NormalizedOddsSnapshot,
    NormalizedPlayerBoxscore,
    NormalizedTeamBoxscore,
)


def _fetch_league_id(session: Session, league_code: str) -> int:
    stmt = select(db_models.SportsLeague.id).where(db_models.SportsLeague.code == league_code)
    league_id = session.execute(stmt).scalar()
    if league_id is None:
        msg = f"League code {league_code} not found. Seed sports_leagues first."
        raise ValueError(msg)
    return league_id


def _upsert_team(session: Session, league_id: int, identity) -> int:
    team_name = identity.name
    short_name = identity.short_name or team_name
    abbreviation = identity.abbreviation or (short_name or team_name)[:6].upper()
    
    stmt = (
        insert(db_models.SportsTeam)
        .values(
            league_id=league_id,
            external_ref=identity.external_ref,
            name=team_name,
            short_name=short_name,
            abbreviation=abbreviation,
            location=None,
            external_codes={},
        )
        .on_conflict_do_update(
            index_elements=["league_id", "abbreviation"],
            set_={
                "name": team_name,
                "short_name": short_name,
                "external_ref": identity.external_ref,
                "updated_at": datetime.utcnow(),
            },
        )
        .returning(db_models.SportsTeam.id)
    )
    result = session.execute(stmt).scalar_one()
    return int(result)


def _team_ids(session: Session, league_id: int, game_identity: GameIdentification) -> tuple[int, int]:
    home_team_id = _upsert_team(session, league_id, game_identity.home_team)
    away_team_id = _upsert_team(session, league_id, game_identity.away_team)
    return home_team_id, away_team_id


def upsert_game(session: Session, normalized: NormalizedGame) -> int:
    league_id = _fetch_league_id(session, normalized.identity.league_code)
    home_team_id, away_team_id = _team_ids(session, league_id, normalized.identity)

    stmt = (
        insert(db_models.SportsGame)
        .values(
            league_id=league_id,
            season=normalized.identity.season,
            season_type=normalized.identity.season_type,
            game_date=normalized.identity.game_date,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=normalized.home_score,
            away_score=normalized.away_score,
            venue=normalized.venue,
            status=normalized.status,
            source_game_key=normalized.identity.source_game_key,
            scrape_version=1,
            last_scraped_at=datetime.utcnow(),
            external_ids={},
        )
        .on_conflict_do_update(
            constraint="uq_game_identity",
            set_={
                "home_score": normalized.home_score,
                "away_score": normalized.away_score,
                "status": normalized.status,
                "venue": normalized.venue,
                "scrape_version": db_models.SportsGame.scrape_version + 1,
                "last_scraped_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )
        .returning(db_models.SportsGame.id)
    )
    game_id = session.execute(stmt).scalar_one()
    return int(game_id)


def _build_team_stats(payload: NormalizedTeamBoxscore) -> dict:
    """Build stats dict from typed fields + raw_stats, excluding None values."""
    stats = {}
    # Add typed fields if not None
    if payload.points is not None:
        stats["points"] = payload.points
    if payload.rebounds is not None:
        stats["rebounds"] = payload.rebounds
    if payload.assists is not None:
        stats["assists"] = payload.assists
    if payload.turnovers is not None:
        stats["turnovers"] = payload.turnovers
    if payload.passing_yards is not None:
        stats["passing_yards"] = payload.passing_yards
    if payload.rushing_yards is not None:
        stats["rushing_yards"] = payload.rushing_yards
    if payload.receiving_yards is not None:
        stats["receiving_yards"] = payload.receiving_yards
    if payload.hits is not None:
        stats["hits"] = payload.hits
    if payload.runs is not None:
        stats["runs"] = payload.runs
    if payload.errors is not None:
        stats["errors"] = payload.errors
    if payload.shots_on_goal is not None:
        stats["shots_on_goal"] = payload.shots_on_goal
    if payload.penalty_minutes is not None:
        stats["penalty_minutes"] = payload.penalty_minutes
    # Merge in raw_stats (allows scraper to add additional fields)
    if payload.raw_stats:
        stats.update(payload.raw_stats)
    return stats


def upsert_team_boxscores(session: Session, game_id: int, payloads: Sequence[NormalizedTeamBoxscore]) -> None:
    for payload in payloads:
        league_id = _fetch_league_id(session, payload.team.league_code)
        team_id = _upsert_team(session, league_id, payload.team)
        stats = _build_team_stats(payload)
        stmt = (
            insert(db_models.SportsTeamBoxscore)
            .values(
                game_id=game_id,
                team_id=team_id,
                is_home=payload.is_home,
                stats=stats,
                source="sports_reference",
            )
            .on_conflict_do_update(
                constraint="uq_team_boxscore_game_team",
                set_={
                    "stats": stats,
                    "updated_at": datetime.utcnow(),
                },
            )
        )
        session.execute(stmt)


def _build_player_stats(payload: NormalizedPlayerBoxscore) -> dict:
    """Build stats dict from typed fields + raw_stats, excluding None values."""
    stats = {}
    # Add typed fields if not None
    if payload.minutes is not None:
        stats["minutes"] = payload.minutes
    if payload.points is not None:
        stats["points"] = payload.points
    if payload.rebounds is not None:
        stats["rebounds"] = payload.rebounds
    if payload.assists is not None:
        stats["assists"] = payload.assists
    if payload.yards is not None:
        stats["yards"] = payload.yards
    if payload.touchdowns is not None:
        stats["touchdowns"] = payload.touchdowns
    if payload.shots_on_goal is not None:
        stats["shots_on_goal"] = payload.shots_on_goal
    if payload.penalties is not None:
        stats["penalties"] = payload.penalties
    # Merge in raw_stats (allows scraper to add additional fields)
    if payload.raw_stats:
        stats.update(payload.raw_stats)
    return stats


def upsert_player_boxscores(session: Session, game_id: int, payloads: Sequence[NormalizedPlayerBoxscore]) -> None:
    for payload in payloads:
        league_id = _fetch_league_id(session, payload.team.league_code)
        team_id = _upsert_team(session, league_id, payload.team)
        stats = _build_player_stats(payload)
        stmt = (
            insert(db_models.SportsPlayerBoxscore)
            .values(
                game_id=game_id,
                team_id=team_id,
                player_external_ref=payload.player_id,
                player_name=payload.player_name,
                stats=stats,
                source="sports_reference",
            )
            .on_conflict_do_update(
                constraint="uq_player_boxscore_identity",
                set_={
                    "stats": stats,
                    "updated_at": datetime.utcnow(),
                },
            )
        )
        session.execute(stmt)


def upsert_odds(session: Session, snapshot: NormalizedOddsSnapshot) -> None:
    league_id = _fetch_league_id(session, snapshot.league_code)
    home_team_id = _upsert_team(session, league_id, snapshot.home_team)
    away_team_id = _upsert_team(session, league_id, snapshot.away_team)

    stmt = (
        select(db_models.SportsGame.id)
        .where(db_models.SportsGame.league_id == league_id)
        .where(db_models.SportsGame.home_team_id == home_team_id)
        .where(db_models.SportsGame.away_team_id == away_team_id)
        .where(db_models.SportsGame.game_date == snapshot.game_date)
    )
    game_id = session.execute(stmt).scalar()
    if game_id is None:
        logger.warning(
            "odds_game_missing",
            league=snapshot.league_code,
            home=snapshot.home_team.abbreviation,
            away=snapshot.away_team.abbreviation,
        )
        return

    stmt = (
        insert(db_models.SportsGameOdds)
        .values(
            game_id=game_id,
            book=snapshot.book,
            market_type=snapshot.market_type,
            side=snapshot.side,
            line=snapshot.line,
            price=snapshot.price,
            is_closing_line=snapshot.is_closing_line,
            observed_at=snapshot.observed_at,
            source_key=snapshot.source_key,
            raw_payload=snapshot.raw_payload,
        )
        .on_conflict_do_update(
            index_elements=["game_id", "book", "market_type", "is_closing_line"],
            set_={
                "line": snapshot.line,
                "price": snapshot.price,
                "observed_at": snapshot.observed_at,
                "source_key": snapshot.source_key,
                "raw_payload": snapshot.raw_payload,
                "updated_at": datetime.utcnow(),
            },
        )
    )
    session.execute(stmt)


def persist_game_payload(session: Session, payload: NormalizedGame) -> int:
    game_id = upsert_game(session, payload)
    upsert_team_boxscores(session, game_id, payload.team_boxscores)
    if payload.player_boxscores:
        upsert_player_boxscores(session, game_id, payload.player_boxscores)
    return game_id


