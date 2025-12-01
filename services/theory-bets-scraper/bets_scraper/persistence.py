"""Persistence helpers for normalized scraper payloads."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Sequence

from sqlalchemy import bindparam, func, or_, select
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
    """Get league ID by code. Uses shared utility."""
    from ..utils.db_queries import get_league_id
    return get_league_id(session, league_code)


def _upsert_team(session: Session, league_id: int, identity) -> int:
    team_name = identity.name
    short_name = identity.short_name or team_name
    # Always use abbreviation from normalization - never generate
    if not identity.abbreviation:
        raise ValueError(f"Team identity must have abbreviation: {team_name}")
    abbreviation = identity.abbreviation
    
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
            index_elements=["league_id", "name"],  # Changed from abbreviation
            set_={
                "short_name": short_name,
                "abbreviation": abbreviation,  # Update abbreviation if different
                "external_ref": identity.external_ref,
                "updated_at": utcnow(),
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

    conflict_updates = {
        "home_score": normalized.home_score,
        "away_score": normalized.away_score,
        "status": normalized.status,
        "venue": normalized.venue,
        "scrape_version": db_models.SportsGame.scrape_version + 1,
        "last_scraped_at": utcnow(),
        "updated_at": utcnow(),
    }

    base_stmt = insert(db_models.SportsGame).values(
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
        last_scraped_at=utcnow(),
        external_ids={},
    )

    if normalized.identity.source_game_key:
        stmt = base_stmt.on_conflict_do_update(
            index_elements=["source_game_key"],
            set_=conflict_updates,
        )
    else:
        stmt = base_stmt.on_conflict_do_update(
            constraint="uq_game_identity",
            set_=conflict_updates,
        )

    stmt = stmt.returning(db_models.SportsGame.id)
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
                    "updated_at": utcnow(),
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
                    "updated_at": utcnow(),
                },
            )
        )
        session.execute(stmt)


def _find_team_by_name(
    session: Session,
    league_id: int,
    team_name: str,
    team_abbr: str | None = None,
) -> int | None:
    """Find existing team by name (exact or normalized match).
    
    This function tries multiple strategies to find a matching team:
    1. Exact match on name or short_name
    2. If team_name contains a space, try matching the first word (city name)
    3. Match by abbreviation
    4. Prefer teams with more games (more established)
    """
    from ..utils.db_queries import count_team_games

    def team_usage(team_id: int) -> int:
        return count_team_games(session, team_id)

    candidate_ids: list[int] = []

    # 1. Exact match (case-insensitive)
    exact_match_stmt = (
        select(db_models.SportsTeam.id)
        .where(db_models.SportsTeam.league_id == league_id)
        .where(
            or_(
                db_models.SportsTeam.name == team_name,
                db_models.SportsTeam.short_name == team_name,
                func.lower(db_models.SportsTeam.name) == func.lower(team_name),
                func.lower(db_models.SportsTeam.short_name) == func.lower(team_name),
            )
        )
        .limit(1)
    )
    exact_match_id = session.execute(exact_match_stmt).scalar()
    if exact_match_id is not None:
        candidate_ids.append(exact_match_id)

    # 2. If team_name has multiple words, try matching first word (city name)
    # This handles "Atlanta Hawks" matching "Atlanta" or vice versa
    if team_name and " " in team_name:
        first_word = team_name.split()[0]  # e.g., "Atlanta" from "Atlanta Hawks"
        base_stmt = (
            select(db_models.SportsTeam.id)
            .where(db_models.SportsTeam.league_id == league_id)
            .where(
                or_(
                    db_models.SportsTeam.name == first_word,
                    db_models.SportsTeam.short_name == first_word,
                    func.lower(db_models.SportsTeam.name) == func.lower(first_word),
                    func.lower(db_models.SportsTeam.short_name) == func.lower(first_word),
                    # Also check if existing team name starts with the first word
                    func.lower(db_models.SportsTeam.name).like(func.lower(first_word) + "%"),
                    func.lower(db_models.SportsTeam.short_name).like(func.lower(first_word) + "%"),
                )
            )
        )
        base_matches = [row[0] for row in session.execute(base_stmt).all()]
        candidate_ids.extend(base_matches)
    
    # 3. Also try matching if team_name is a single word and existing team name starts with it
    # This handles "Atlanta" matching "Atlanta Hawks"
    elif team_name:
        single_word_stmt = (
            select(db_models.SportsTeam.id)
            .where(db_models.SportsTeam.league_id == league_id)
            .where(
                or_(
                    func.lower(db_models.SportsTeam.name).like(func.lower(team_name) + "%"),
                    func.lower(db_models.SportsTeam.short_name).like(func.lower(team_name) + "%"),
                )
            )
        )
        single_word_matches = [row[0] for row in session.execute(single_word_stmt).all()]
        candidate_ids.extend(single_word_matches)

    # 4. Match by abbreviation
    if team_abbr:
        stmt = (
            select(db_models.SportsTeam.id)
            .where(db_models.SportsTeam.league_id == league_id)
            .where(func.upper(db_models.SportsTeam.abbreviation) == func.upper(team_abbr))
        )
        abbr_matches = [row[0] for row in session.execute(stmt).all()]
        candidate_ids.extend(abbr_matches)

    if not candidate_ids:
        return None

    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for cid in candidate_ids:
        if cid not in seen:
            seen.add(cid)
            unique_candidates.append(cid)

    # Prefer: 1) Teams that match canonical name from normalization, 2) Full team names, 3) Most games
    # Import normalization to check canonical names
    from ..normalization import normalize_team_name
    
    # Get league code for normalization
    league = session.get(db_models.SportsLeague, league_id)
    league_code = league.code if league else None
    
    def team_score(team_id: int) -> tuple[int, int, int]:
        """Return (matches_canonical, has_full_name, game_count) for sorting.
        - 10000 points if name matches canonical from normalization
        - 1000 points if has space (full name vs city-only)
        - game_count as tiebreaker
        """
        team = session.get(db_models.SportsTeam, team_id)
        if not team:
            return (0, 0, 0)
        
        # Check if matches canonical name
        matches_canonical = False
        if league_code:
            canonical_name, _ = normalize_team_name(league_code, team.name)
            matches_canonical = (team.name == canonical_name)
        
        has_full_name = " " in team.name
        usage = team_usage(team_id)
        return (10000 if matches_canonical else 0, 1000 if has_full_name else 0, usage)
    
    # Sort candidates by score (canonical matches first, then full names, then game count)
    scored_candidates = [(team_score(cid), cid) for cid in unique_candidates]
    scored_candidates.sort(reverse=True)
    best_id = scored_candidates[0][1]

    return best_id


def upsert_odds(session: Session, snapshot: NormalizedOddsSnapshot) -> None:
    league_id = _fetch_league_id(session, snapshot.league_code)
    
    # Try to find existing teams by name first (to reuse scraper teams)
    home_team_id = _find_team_by_name(session, league_id, snapshot.home_team.name, snapshot.home_team.abbreviation)
    if home_team_id is None:
        logger.debug(
            "odds_team_not_found_creating",
            team_name=snapshot.home_team.name,
            abbreviation=snapshot.home_team.abbreviation,
            league=snapshot.league_code,
        )
        home_team_id = _upsert_team(session, league_id, snapshot.home_team)
    else:
        logger.debug(
            "odds_team_found",
            team_name=snapshot.home_team.name,
            team_id=home_team_id,
            league=snapshot.league_code,
        )
    
    away_team_id = _find_team_by_name(session, league_id, snapshot.away_team.name, snapshot.away_team.abbreviation)
    if away_team_id is None:
        logger.debug(
            "odds_team_not_found_creating",
            team_name=snapshot.away_team.name,
            abbreviation=snapshot.away_team.abbreviation,
            league=snapshot.league_code,
        )
        away_team_id = _upsert_team(session, league_id, snapshot.away_team)
    else:
        logger.debug(
            "odds_team_found",
            team_name=snapshot.away_team.name,
            team_id=away_team_id,
            league=snapshot.league_code,
        )
    
    # Fix game date matching (use date range instead of exact datetime)
    # Games are stored at midnight for that date, but odds use actual tipoff times
    game_day = snapshot.game_date.date()
    day_start = datetime.combine(game_day - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    day_end = datetime.combine(game_day + timedelta(days=1), datetime.max.time(), tzinfo=timezone.utc)
    
    # First, check if any games exist for these teams on this date
    games_check = (
        select(db_models.SportsGame.id, db_models.SportsGame.game_date, db_models.SportsGame.home_team_id, db_models.SportsGame.away_team_id)
        .where(db_models.SportsGame.league_id == league_id)
        .where(db_models.SportsGame.game_date >= day_start)
        .where(db_models.SportsGame.game_date <= day_end)
        .where(
            or_(
                db_models.SportsGame.home_team_id == home_team_id,
                db_models.SportsGame.away_team_id == home_team_id,
                db_models.SportsGame.home_team_id == away_team_id,
                db_models.SportsGame.away_team_id == away_team_id,
            )
        )
        .limit(10)
    )
    potential_games = session.execute(games_check).all()
    
    stmt = (
        select(db_models.SportsGame.id)
        .where(db_models.SportsGame.league_id == league_id)
        .where(db_models.SportsGame.home_team_id == home_team_id)
        .where(db_models.SportsGame.away_team_id == away_team_id)
        .where(db_models.SportsGame.game_date >= day_start)
        .where(db_models.SportsGame.game_date <= day_end)
    )
    game_id = session.execute(stmt).scalar()
    if game_id is None:
        swap_stmt = (
            select(db_models.SportsGame.id)
            .where(db_models.SportsGame.league_id == league_id)
            .where(db_models.SportsGame.home_team_id == away_team_id)
            .where(db_models.SportsGame.away_team_id == home_team_id)
            .where(db_models.SportsGame.game_date >= day_start)
            .where(db_models.SportsGame.game_date <= day_end)
        )
        swapped_game_id = session.execute(swap_stmt).scalar()
        if swapped_game_id is not None:
            logger.info(
                "odds_game_matched_swapped",
                league=snapshot.league_code,
                requested_home=snapshot.home_team.abbreviation,
                requested_away=snapshot.away_team.abbreviation,
                matched_as_home=snapshot.away_team.abbreviation,
                matched_as_away=snapshot.home_team.abbreviation,
                game_date=str(snapshot.game_date.date()),
                game_id=swapped_game_id,
            )
            game_id = swapped_game_id

    if game_id is None:
        # Get team names for better debugging
        home_team = session.execute(
            select(db_models.SportsTeam.name, db_models.SportsTeam.abbreviation)
            .where(db_models.SportsTeam.id == home_team_id)
        ).first()
        away_team = session.execute(
            select(db_models.SportsTeam.name, db_models.SportsTeam.abbreviation)
            .where(db_models.SportsTeam.id == away_team_id)
        ).first()
        
        logger.warning(
            "odds_game_missing",
            league=snapshot.league_code,
            home_team_name=snapshot.home_team.name,
            home_team_abbr=snapshot.home_team.abbreviation,
            home_team_id=home_team_id,
            home_team_db_name=home_team[0] if home_team else None,
            home_team_db_abbr=home_team[1] if home_team else None,
            away_team_name=snapshot.away_team.name,
            away_team_abbr=snapshot.away_team.abbreviation,
            away_team_id=away_team_id,
            away_team_db_name=away_team[0] if away_team else None,
            away_team_db_abbr=away_team[1] if away_team else None,
            game_date=str(snapshot.game_date.date()),
            game_datetime=str(snapshot.game_date),
            day_start=str(day_start),
            day_end=str(day_end),
            potential_games_count=len(potential_games),
            potential_games=[{"id": g[0], "date": str(g[1]), "home_id": g[2], "away_id": g[3]} for g in potential_games[:5]],
        )
        return False

    side_value = snapshot.side[:20] if snapshot.side else None

    stmt = (
        insert(db_models.SportsGameOdds)
        .values(
            game_id=game_id,
            book=snapshot.book,
            market_type=snapshot.market_type,
            side=side_value,
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
                "updated_at": utcnow(),
            },
        )
    )
    session.execute(stmt)
    return True


def persist_game_payload(session: Session, payload: NormalizedGame) -> int:
    game_id = upsert_game(session, payload)
    upsert_team_boxscores(session, game_id, payload.team_boxscores)
    
    logger.info(
        "persist_game_payload",
        game_id=game_id,
        game_key=payload.identity.source_game_key,
        team_boxscores_count=len(payload.team_boxscores),
        player_boxscores_count=len(payload.player_boxscores) if payload.player_boxscores else 0,
    )
    
    if payload.player_boxscores:
        logger.debug("persisting_player_boxscores", game_id=game_id, count=len(payload.player_boxscores))
        upsert_player_boxscores(session, game_id, payload.player_boxscores)
    else:
        logger.warning("no_player_boxscores_to_persist", game_id=game_id, game_key=payload.identity.source_game_key)
    return game_id


