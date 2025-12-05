"""Compute generated features for a set of games.

This module takes the generated feature descriptors and produces per-game
feature values using available boxscore data and simple context signals
(rest days, rolling averages).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import Float, Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import db_models
from .feature_engine import GeneratedFeature


def _to_numeric(val: Any) -> float | None:
    """Convert a stat value to a numeric type, handling strings, None, and various formats."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # Handle time strings like "30:18" (minutes:seconds)
        if ":" in val:
            try:
                parts = val.split(":")
                return float(parts[0]) + float(parts[1]) / 60 if len(parts) == 2 else None
            except (ValueError, IndexError):
                return None
        # Try direct float conversion
        try:
            return float(val)
        except ValueError:
            return None
    return None


async def _previous_game_dates(
    session: AsyncSession, team_ids: set[int], game_dates: dict[int, datetime]
) -> dict[int, datetime | None]:
    """Fetch the most recent game date before the provided game_date for each team."""
    results: dict[int, datetime | None] = {}
    for team_id in team_ids:
        target_date = game_dates.get(team_id)
        if not target_date:
            results[team_id] = None
            continue
        stmt: Select = (
            select(db_models.SportsGame.game_date)
            .where(
                db_models.SportsGame.status == db_models.GameStatus.completed,
                db_models.SportsGame.game_date < target_date,
                (db_models.SportsGame.home_team_id == team_id)
                | (db_models.SportsGame.away_team_id == team_id),
            )
            .order_by(desc(db_models.SportsGame.game_date))
            .limit(1)
        )
        res = await session.execute(stmt)
        results[team_id] = res.scalar_one_or_none()
    return results


async def _rolling_average(
    session: AsyncSession, team_id: int, game_date: datetime, stat: str, window: int
) -> float | None:
    """Compute a simple rolling average for a stat over last N games before game_date."""
    # First, get the last N boxscore IDs
    boxscore_ids_stmt: Select = (
        select(db_models.SportsTeamBoxscore.id)
        .join(db_models.SportsGame, db_models.SportsTeamBoxscore.game_id == db_models.SportsGame.id)
        .where(
            (db_models.SportsTeamBoxscore.team_id == team_id),
            (db_models.SportsGame.game_date < game_date),
        )
        .order_by(desc(db_models.SportsGame.game_date))
        .limit(window)
    )
    boxscore_ids_result = await session.execute(boxscore_ids_stmt)
    boxscore_ids = [row[0] for row in boxscore_ids_result]

    if not boxscore_ids:
        return None

    # Then average the stat values from those boxscores, safely casting to float and ignoring blanks
    stat_value = func.nullif(db_models.SportsTeamBoxscore.stats[stat].as_string(), "").cast(Float)
    stmt: Select = select(func.avg(stat_value)).where(
        db_models.SportsTeamBoxscore.id.in_(boxscore_ids),
        stat_value.isnot(None),
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def compute_features_for_games(
    session: AsyncSession,
    league_id: int,
    game_ids: Iterable[int],
    features: list[GeneratedFeature],
) -> list[dict[str, Any]]:
    """Compute feature values for a set of games.

    Returns a list of dicts: {\"game_id\": id, <feature>: value}
    """
    # Load games with boxscores and teams
    stmt: Select = (
        select(db_models.SportsGame)
        .where(db_models.SportsGame.id.in_(list(game_ids)), db_models.SportsGame.league_id == league_id)
        .options(
            selectinload(db_models.SportsGame.team_boxscores).selectinload(db_models.SportsTeamBoxscore.team),
            selectinload(db_models.SportsGame.home_team),
            selectinload(db_models.SportsGame.away_team),
        )
    )
    games_result = await session.execute(stmt)
    games: list[db_models.SportsGame] = games_result.scalars().all()

    # Prepare helper maps
    team_ids: set[int] = set()
    team_date_lookup: dict[int, datetime] = {}
    for game in games:
        if game.home_team_id:
            team_ids.add(game.home_team_id)
            team_date_lookup[game.home_team_id] = game.game_date
        if game.away_team_id:
            team_ids.add(game.away_team_id)
            team_date_lookup[game.away_team_id] = game.game_date

    prev_dates = await _previous_game_dates(session, team_ids, team_date_lookup)

    rows: list[dict[str, Any]] = []
    for game in games:
        row: dict[str, Any] = {"game_id": game.id}

        # Build maps for quick stat lookup
        home_stats: dict[str, Any] = {}
        away_stats: dict[str, Any] = {}
        for box in game.team_boxscores:
            if box.is_home:
                home_stats = box.stats or {}
            else:
                away_stats = box.stats or {}

        for f in features:
            name = f.name
            if f.category == "raw":
                if name.startswith("home_"):
                    stat = name.removeprefix("home_")
                    row[name] = home_stats.get(stat)
                elif name.startswith("away_"):
                    stat = name.removeprefix("away_")
                    row[name] = away_stats.get(stat)
            elif f.category == "differential":
                stat = name.removesuffix("_diff")
                home_val = _to_numeric(home_stats.get(stat))
                away_val = _to_numeric(away_stats.get(stat))
                if home_val is not None and away_val is not None:
                    row[name] = home_val - away_val
            elif f.category == "combined":
                stat = name.removeprefix("total_")
                home_val = _to_numeric(home_stats.get(stat))
                away_val = _to_numeric(away_stats.get(stat))
                if home_val is not None and away_val is not None:
                    row[name] = home_val + away_val
            elif f.category == "situational":
                if name == "home_rest_days" and game.home_team_id:
                    prev = prev_dates.get(game.home_team_id)
                    row[name] = (game.game_date - prev).days if prev else None
                if name == "away_rest_days" and game.away_team_id:
                    prev = prev_dates.get(game.away_team_id)
                    row[name] = (game.game_date - prev).days if prev else None
                if name == "rest_advantage":
                    home_rd = row.get("home_rest_days")
                    away_rd = row.get("away_rest_days")
                    if home_rd is not None and away_rd is not None:
                        row[name] = home_rd - away_rd
            elif f.category == "rolling":
                # naming: rolling_{stat}_{window}_home/away/diff
                # Note: stat can contain underscores (e.g., "fg_pct"), so parse from the end
                if not name.startswith("rolling_"):
                    continue
                parts = name.removeprefix("rolling_").split("_")
                # Expected: ["<stat>", "<stat>", ..., "<window>", "<side>"]
                # Parse from the end: last is side, second-to-last is window, rest is stat
                if len(parts) >= 3:
                    side = parts[-1]  # last part
                    try:
                        window = int(parts[-2])  # second-to-last part
                    except (ValueError, IndexError):
                        continue  # Skip if window is not numeric
                    stat = "_".join(parts[:-2])  # everything before window and side
                    
                    if side == "home" and game.home_team_id:
                        val = await _rolling_average(session, game.home_team_id, game.game_date, stat, window)
                        row[name] = val
                    elif side == "away" and game.away_team_id:
                        val = await _rolling_average(session, game.away_team_id, game.game_date, stat, window)
                        row[name] = val
                    elif side == "diff":
                        home_name = f"rolling_{stat}_{window}_home"
                        away_name = f"rolling_{stat}_{window}_away"
                        if home_name in row and away_name in row:
                            hv = _to_numeric(row.get(home_name))
                            av = _to_numeric(row.get(away_name))
                            if hv is not None and av is not None:
                                row[name] = hv - av

        rows.append(row)

    return rows

