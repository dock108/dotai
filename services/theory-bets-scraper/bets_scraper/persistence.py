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
    stmt = (
        insert(db_models.SportsTeam)
        .values(
            league_id=league_id,
            external_ref=identity.external_ref,
            name=identity.name,
            short_name=identity.short_name or identity.name,
            abbreviation=identity.abbreviation or (identity.short_name or identity.name)[:6].upper(),
            location=None,
            external_codes={},
        )
        .on_conflict_do_update(
            index_elements=["league_id", "abbreviation"],
            set_={
                "name": identity.name,
                "short_name": identity.short_name or identity.name,
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


def upsert_team_boxscores(session: Session, game_id: int, payloads: Sequence[NormalizedTeamBoxscore]) -> None:
    for payload in payloads:
        league_id = _fetch_league_id(session, payload.team.league_code)
        team_id = _upsert_team(session, league_id, payload.team)
        stmt = (
            insert(db_models.SportsTeamBoxscore)
            .values(
                game_id=game_id,
                team_id=team_id,
                is_home=payload.is_home,
                points=payload.points,
                rebounds=payload.rebounds,
                assists=payload.assists,
                turnovers=payload.turnovers,
                passing_yards=payload.passing_yards,
                rushing_yards=payload.rushing_yards,
                receiving_yards=payload.receiving_yards,
                hits=payload.hits,
                runs=payload.runs,
                errors=payload.errors,
                shots_on_goal=payload.shots_on_goal,
                penalty_minutes=payload.penalty_minutes,
                raw_stats_json=payload.raw_stats,
                source="sports_reference",
            )
            .on_conflict_do_update(
                constraint="uq_team_boxscore_game_team",
                set_={
                    "points": payload.points,
                    "rebounds": payload.rebounds,
                    "assists": payload.assists,
                    "turnovers": payload.turnovers,
                    "passing_yards": payload.passing_yards,
                    "rushing_yards": payload.rushing_yards,
                    "receiving_yards": payload.receiving_yards,
                    "hits": payload.hits,
                    "runs": payload.runs,
                    "errors": payload.errors,
                    "shots_on_goal": payload.shots_on_goal,
                    "penalty_minutes": payload.penalty_minutes,
                    "raw_stats_json": payload.raw_stats,
                    "updated_at": datetime.utcnow(),
                },
            )
        )
        session.execute(stmt)


def upsert_player_boxscores(session: Session, game_id: int, payloads: Sequence[NormalizedPlayerBoxscore]) -> None:
    for payload in payloads:
        league_id = _fetch_league_id(session, payload.team.league_code)
        team_id = _upsert_team(session, league_id, payload.team)
        stmt = (
            insert(db_models.SportsPlayerBoxscore)
            .values(
                game_id=game_id,
                team_id=team_id,
                player_external_ref=payload.player_id,
                player_name=payload.player_name,
                minutes=payload.minutes,
                points=payload.points,
                rebounds=payload.rebounds,
                assists=payload.assists,
                yards=payload.yards,
                touchdowns=payload.touchdowns,
                shots_on_goal=payload.shots_on_goal,
                penalties=payload.penalties,
                raw_stats_json=payload.raw_stats,
                source="sports_reference",
            )
            .on_conflict_do_update(
                constraint="uq_player_boxscore_identity",
                set_={
                    "minutes": payload.minutes,
                    "points": payload.points,
                    "rebounds": payload.rebounds,
                    "assists": payload.assists,
                    "yards": payload.yards,
                    "touchdowns": payload.touchdowns,
                    "shots_on_goal": payload.shots_on_goal,
                    "penalties": payload.penalties,
                    "raw_stats_json": payload.raw_stats,
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


