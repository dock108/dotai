"""Compute generated features for a set of games.

This module takes the generated feature descriptors and produces per-game
feature values using available boxscore data and simple context signals
(rest days, rolling averages).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping

from sqlalchemy import Float, Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import db_models
from .feature_engine import GeneratedFeature
from .derived_metrics import compute_derived_metrics
from engine.common.feature_builder import FeatureBuilder
from .feature_metadata import FeatureTiming, get_feature_metadata


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


def _estimate_possessions(stats: Mapping[str, Any]) -> float | None:
    """Estimate possessions using basic boxscore fields."""
    try:
        fga = float(stats.get("fga", stats.get("fg", 0)) or 0)
        fta = float(stats.get("fta", 0) or 0)
        orb = float(stats.get("orb", stats.get("oreb", 0)) or 0)
        tov = float(stats.get("tov", stats.get("turnovers", 0)) or 0)
    except (TypeError, ValueError):
        return None
    poss = fga - orb + tov + 0.475 * fta
    return poss if poss > 0 else None


def _build_event_payload(
    game: db_models.SportsGame,
    league_id: int,
    metrics: Mapping[str, Any],
    home_stats: Mapping[str, Any],
    away_stats: Mapping[str, Any],
    pace_block: Mapping[str, Any],
) -> dict[str, Any]:
    """Construct a generic event payload for layered feature builders."""
    metadata = {
        "game_id": game.id,
        "league_id": league_id,
        "game_date": game.game_date,
        "season": getattr(game, "season", None),
        "home_team": game.home_team.name if game.home_team else None,
        "away_team": game.away_team.name if game.away_team else None,
    }

    closing = {
        "closing_ml_home": metrics.get("closing_ml_home"),
        "closing_ml_away": metrics.get("closing_ml_away"),
    }

    lines = {
        "closing_spread_home": metrics.get("closing_spread_home"),
        "closing_spread_home_price": metrics.get("closing_spread_home_price"),
        "closing_spread_away": metrics.get("closing_spread_away"),
        "closing_spread_away_price": metrics.get("closing_spread_away_price"),
        "closing_total": metrics.get("closing_total"),
        "closing_total_price": metrics.get("closing_total_price"),
    }

    result = {
        "home_score": metrics.get("home_score"),
        "away_score": metrics.get("away_score"),
        "winner": metrics.get("winner"),
        "did_home_cover": metrics.get("did_home_cover"),
        "did_away_cover": metrics.get("did_away_cover"),
        "total_result": metrics.get("total_result"),
        "margin_of_victory": metrics.get("margin_of_victory"),
        "combined_score": metrics.get("combined_score"),
    }

    ratings = {
        "home_rating": home_stats.get("team_rating") or home_stats.get("rating"),
        "away_rating": away_stats.get("team_rating") or away_stats.get("rating"),
        "home_rating_trend": home_stats.get("rating_trend"),
        "away_rating_trend": away_stats.get("rating_trend"),
    }

    projections = {
        "home_proj_points": home_stats.get("proj_points") or home_stats.get("projected_points"),
        "away_proj_points": away_stats.get("proj_points") or away_stats.get("projected_points"),
        "home_proj_reb": home_stats.get("proj_reb") or home_stats.get("projected_rebounds"),
        "away_proj_reb": away_stats.get("proj_reb") or away_stats.get("projected_rebounds"),
        "home_proj_ast": home_stats.get("proj_ast") or home_stats.get("projected_assists"),
        "away_proj_ast": away_stats.get("proj_ast") or away_stats.get("projected_assists"),
    }

    pace = pace_block

    return {
        "metadata": metadata,
        "closing": closing,
        "lines": lines,
        "result": result,
        "ratings": ratings,
        "projections": projections,
        "pace": pace,
        "metrics": metrics,
        "stats": {"home": home_stats, "away": away_stats},
    }


async def compute_features_for_games(
    session: AsyncSession,
    league_id: int,
    game_ids: Iterable[int],
    features: list[GeneratedFeature],
    layer_builder: FeatureBuilder | None = None,
    context: str = "deployable",
) -> list[dict[str, Any]]:
    """Compute feature values for a set of games.

    Returns a list of dicts: {\"game_id\": id, <feature>: value}
    """
    # Load games with boxscores, teams, and odds (for closing lines)
    stmt: Select = (
        select(db_models.SportsGame)
        .where(db_models.SportsGame.id.in_(list(game_ids)), db_models.SportsGame.league_id == league_id)
        .options(
            selectinload(db_models.SportsGame.team_boxscores).selectinload(db_models.SportsTeamBoxscore.team),
            selectinload(db_models.SportsGame.home_team),
            selectinload(db_models.SportsGame.away_team),
            selectinload(db_models.SportsGame.odds),
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

    requested_names = {f.name for f in features}
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
        # Pace estimation from boxscore stats (only if requested)
        wants_pace = any(k in requested_names for k in ("pace_home_possessions", "pace_away_possessions", "pace_game"))
        if wants_pace:
            poss_home = _estimate_possessions(home_stats)
            poss_away = _estimate_possessions(away_stats)
            pace_game = None
            if poss_home is not None and poss_away is not None:
                pace_game = (poss_home + poss_away) / 2.0
                if "pace_home_possessions" in requested_names:
                    row["pace_home_possessions"] = poss_home
                if "pace_away_possessions" in requested_names:
                    row["pace_away_possessions"] = poss_away
                if "pace_game" in requested_names:
                    row["pace_game"] = pace_game

        # Derived gaps from metrics (total, cover margin) if requested
        wants_postgame = any(k in requested_names for k in ("final_total_points", "total_delta", "cover_margin"))
        if wants_postgame:
            metrics = compute_derived_metrics(game, game.odds or [])
            if "final_total_points" in requested_names and "combined_score" in metrics:
                row["final_total_points"] = metrics.get("combined_score")
            if "total_delta" in requested_names and "closing_total" in metrics and "combined_score" in metrics:
                ct = metrics.get("closing_total")
                cs = metrics.get("combined_score")
                if ct is not None and cs is not None:
                    row["total_delta"] = cs - ct
            if "cover_margin" in requested_names and "margin_of_victory" in metrics and "closing_spread_home" in metrics:
                mov = metrics.get("margin_of_victory")
                csh = metrics.get("closing_spread_home")
                if mov is not None and csh is not None:
                    row["cover_margin"] = mov - csh
        # Rating / projections diffs
        hr = row.get("home_rating") or home_stats.get("team_rating") or home_stats.get("rating")
        ar = row.get("away_rating") or away_stats.get("team_rating") or away_stats.get("rating")
        if hr is not None and ar is not None and "rating_diff" in requested_names and "rating_diff" not in row:
            row["rating_diff"] = _to_numeric(hr) - _to_numeric(ar) if (_to_numeric(hr) is not None and _to_numeric(ar) is not None) else None
        hp = row.get("home_proj_points") or home_stats.get("proj_points") or home_stats.get("projected_points")
        ap = row.get("away_proj_points") or away_stats.get("proj_points") or away_stats.get("projected_points")
        if hp is not None and ap is not None and "proj_points_diff" in requested_names and "proj_points_diff" not in row:
            hpv = _to_numeric(hp)
            apv = _to_numeric(ap)
            if hpv is not None and apv is not None:
                row["proj_points_diff"] = hpv - apv
        # Conference flag
        if "is_conference_game" in requested_names:
            row["is_conference_game"] = getattr(game, "is_conference_game", None)

        if layer_builder:
            metrics = compute_derived_metrics(game, game.odds or [])
            pace_block = {
                "pace_home": row.get("pace_home_possessions"),
                "pace_away": row.get("pace_away_possessions"),
                "pace_game": row.get("pace_game"),
            }
            event_payload = _build_event_payload(game, league_id, metrics, home_stats, away_stats, pace_block)
            try:
                layered = layer_builder.build(event_payload)
                if layered:
                    # Only keep layer outputs that are requested OR explicitly allowed by policy.
                    for k, v in layered.items():
                        if v is None:
                            continue
                        if k in requested_names:
                            row[k] = v
                            continue
                        if context == "deployable" and get_feature_metadata(k).timing == FeatureTiming.POST_GAME:
                            continue
                        # If not requested, don't add surprise features.
                        # (Stage 0 principle: no new signal without interpretation.)
            except Exception:
                # Layered builders are best-effort; ignore failures to keep admin mode fast
                pass

        rows.append(row)

    return rows

