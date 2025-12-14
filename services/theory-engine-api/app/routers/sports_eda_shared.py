"""Shared utilities for EDA routers."""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta
from typing import Any

import numpy as np


def _safe_float(val: float | None) -> float | None:
    """Convert NaN/Inf to None for JSON compliance."""
    if val is None:
        return None
    if math.isnan(val) or math.isinf(val):
        return None
    return val
import structlog
from sqlalchemy import Select, func, select, and_, or_
from sqlalchemy.orm import aliased

from .. import db_models
from ..db import AsyncSession
from ..db_models import SportsPlayerBoxscore
from .sports_eda_schemas import (
    CleaningOptions,
    CleaningSummary,
    FeatureQualityStats,
    GeneratedFeature,
    MicroModelRow,
    TargetDefinition,
    TriggerDefinition,
    TheoryMetrics,
    TheoryEvaluation,
)
from .sports_eda_helpers import _target_value

# Re-export from micro module
from .sports_eda_micro import (
    _build_micro_rows,
    _compute_theory_metrics,
    _compute_theory_evaluation,
)

logger = structlog.get_logger("sports-eda")


def _coerce_numeric(val: Any) -> tuple[float | None, bool]:
    """Return (numeric_value, is_non_numeric)."""
    if val is None:
        return None, False
    if isinstance(val, (int, float)):
        return float(val), False
    if isinstance(val, str):
        if val.strip() == "":
            return None, False
        try:
            return float(val), False
        except ValueError:
            return None, True
    return None, True


def _pearson_correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) < 5:
        return None
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    if np.std(x_arr) == 0 or np.std(y_arr) == 0:
        return None
    return _safe_float(float(np.corrcoef(x_arr, y_arr)[0, 1]))


def _build_phase_ranges(league_code: str | None, seasons: list[int] | None, phase: str | None):
    """Build date ranges for NCAAB phases."""
    if not league_code or league_code.upper() != "NCAAB":
        return None
    if not seasons or not phase or phase == "all":
        return None
    ranges: list[tuple[datetime, datetime]] = []
    for s in seasons:
        season_start = datetime(s, 11, 1)
        conf_year = s + 1
        out_end = datetime(conf_year, 1, 1)
        conf_start = out_end
        conf_end = datetime(conf_year, 3, 16)
        post_start = conf_end
        post_end = datetime(conf_year, 4, 16)
        if phase == "out_conf":
            ranges.append((season_start, out_end))
        elif phase == "conf":
            ranges.append((conf_start, conf_end))
        elif phase == "postseason":
            ranges.append((post_start, post_end))
    return ranges if ranges else None


def _apply_base_filters(stmt: Select, league: db_models.SportsLeague, req: Any) -> Select:
    """Apply shared filters (season, date, conference, spreads, team)."""
    stmt = stmt.where(db_models.SportsGame.league_id == league.id)
    seasons = getattr(req, "seasons", None)
    if seasons:
        stmt = stmt.where(db_models.SportsGame.season.in_(seasons))
    date_start = getattr(req, "date_start", None) or getattr(req, "start_date", None)
    date_end = getattr(req, "date_end", None) or getattr(req, "end_date", None)
    if date_start:
        stmt = stmt.where(db_models.SportsGame.game_date >= date_start)
    if date_end:
        stmt = stmt.where(db_models.SportsGame.game_date <= date_end)
    phase = getattr(req, "phase", None)
    phase_ranges = _build_phase_ranges(getattr(league, "code", None), seasons, phase)
    if phase_ranges:
        clauses = [
            and_(db_models.SportsGame.game_date >= start_dt, db_models.SportsGame.game_date < end_dt)
            for start_dt, end_dt in phase_ranges
        ]
        stmt = stmt.where(or_(*clauses))
    recent_days = getattr(req, "recent_days", None)
    if recent_days:
        cutoff = datetime.utcnow() - timedelta(days=recent_days)
        stmt = stmt.where(db_models.SportsGame.game_date >= cutoff)
    spread_min = getattr(req, "home_spread_min", None)
    spread_max = getattr(req, "home_spread_max", None)
    if spread_min is not None or spread_max is not None:
        stmt = stmt.join(db_models.SportsGameOdds, db_models.SportsGameOdds.game_id == db_models.SportsGame.id)
        stmt = stmt.where(db_models.SportsGameOdds.market_type == "spread")
        if spread_min is not None:
            stmt = stmt.where(db_models.SportsGameOdds.line >= spread_min)
        if spread_max is not None:
            stmt = stmt.where(db_models.SportsGameOdds.line <= spread_max)
    team = getattr(req, "team", None)
    if team:
        team_filter = f"%{team.lower()}%"
        away_team = aliased(db_models.SportsTeam)
        stmt = stmt.join(db_models.SportsTeam, db_models.SportsGame.home_team_id == db_models.SportsTeam.id, isouter=True)
        stmt = stmt.join(away_team, db_models.SportsGame.away_team_id == away_team.id, isouter=True)
        stmt = stmt.where(
            or_(
                func.lower(db_models.SportsTeam.name).like(team_filter),
                func.lower(db_models.SportsTeam.short_name).like(team_filter),
                func.lower(db_models.SportsTeam.abbreviation).like(team_filter),
                func.lower(away_team.name).like(team_filter),
                func.lower(away_team.short_name).like(team_filter),
                func.lower(away_team.abbreviation).like(team_filter),
            )
        )
    return stmt


async def _filter_games_by_player(session: AsyncSession, game_ids: list[int], player: str | None) -> list[int]:
    if not player or not game_ids:
        return game_ids
    stmt = (
        select(SportsPlayerBoxscore.game_id)
        .where(SportsPlayerBoxscore.game_id.in_(game_ids))
        .where(func.lower(SportsPlayerBoxscore.player_name).like(f"%{player.lower()}%"))
    )
    res = await session.execute(stmt)
    return [gid for gid, in res.fetchall()]


def _prepare_dataset(
    feature_data: list[dict[str, Any]],
    feature_names: list[str],
    target_map: dict[int, float],
    cleaning: CleaningOptions | None,
) -> tuple[dict[str, list[float]], list[float], list[int], CleaningSummary]:
    aligned_features: dict[str, list[float]] = {name: [] for name in feature_names}
    aligned_target: list[float] = []
    kept_ids: list[int] = []
    raw_rows = 0
    dropped_null = 0
    dropped_non_numeric = 0

    for row in feature_data:
        gid = row.get("game_id")
        if gid not in target_map:
            continue
        raw_rows += 1

        coerced_values: list[float | None] = []
        non_null_count = 0
        any_null = False
        has_non_numeric = False

        for name in feature_names:
            num_val, is_non_numeric = _coerce_numeric(row.get(name))
            if is_non_numeric:
                has_non_numeric = True
            if num_val is not None:
                non_null_count += 1
            else:
                any_null = True
            coerced_values.append(num_val)

        all_null = non_null_count == 0
        drop_row = False
        if cleaning:
            if cleaning.drop_if_non_numeric and has_non_numeric:
                drop_row = True
                dropped_non_numeric += 1
            elif cleaning.drop_if_any_null and any_null:
                drop_row = True
                dropped_null += 1
            elif cleaning.drop_if_all_null and all_null:
                drop_row = True
                dropped_null += 1
            elif cleaning.min_non_null_features is not None and non_null_count < cleaning.min_non_null_features:
                drop_row = True
                dropped_null += 1

        if drop_row:
            continue

        kept_ids.append(gid)
        aligned_target.append(target_map[gid])
        for name, val in zip(feature_names, coerced_values):
            aligned_features[name].append(np.nan if val is None else val)

    summary = CleaningSummary(
        raw_rows=raw_rows,
        rows_after_cleaning=len(aligned_target),
        dropped_null=dropped_null,
        dropped_non_numeric=dropped_non_numeric,
    )
    return aligned_features, aligned_target, kept_ids, summary


def _compute_quality_stats(
    feature_data: list[dict[str, Any]], feature_names: list[str]
) -> dict[str, FeatureQualityStats]:
    rows = len(feature_data)
    stats: dict[str, FeatureQualityStats] = {}
    for name in feature_names:
        nulls = 0
        non_numeric = 0
        numeric_values: list[float] = []
        distinct_values: set[Any] = set()
        for row in feature_data:
            num_val, is_non_numeric = _coerce_numeric(row.get(name))
            if num_val is None and not is_non_numeric:
                nulls += 1
            if is_non_numeric:
                non_numeric += 1
            if num_val is not None:
                numeric_values.append(num_val)
            val = row.get(name)
            if val is not None:
                distinct_values.add(val)

        count = len(numeric_values)
        min_val = min(numeric_values) if numeric_values else None
        max_val = max(numeric_values) if numeric_values else None
        mean_val = _safe_float(float(np.mean(numeric_values))) if numeric_values else None
        null_pct = float(nulls / rows) if rows else 0.0
        stats[name] = FeatureQualityStats(
            nulls=nulls,
            null_pct=null_pct,
            non_numeric=non_numeric,
            distinct_count=len(distinct_values),
            count=count,
            min=min_val,
            max=max_val,
            mean=mean_val,
        )
    return stats


def _drop_target_leakage(features: list[GeneratedFeature], target_def: TargetDefinition) -> list[GeneratedFeature]:
    """Remove features that are direct aliases/proxies of the target (prevents target leakage)."""
    aliases: set[str] = set()
    if target_def.target_class == "stat" and target_def.target_name == "combined_score":
        aliases.update({"combined_score", "final_total_points", "total_points", "total_delta"})
    if not aliases:
        return features
    filtered = [f for f in features if f.name not in aliases]
    dropped = len(features) - len(filtered)
    if dropped:
        logger.info("dropped_target_alias_features", target=target_def.target_name, dropped=dropped, aliases=list(aliases))
    return filtered


async def _player_minutes_map(
    session: AsyncSession, game_ids: list[int], player: str | None, window: int = 5
) -> dict[int, dict[str, float | None]]:
    """Build per-game player minutes + rolling averages."""
    if not player or not game_ids:
        return {}
    stmt = (
        select(db_models.SportsGame.id, db_models.SportsGame.game_date, SportsPlayerBoxscore.stats)
        .join(SportsPlayerBoxscore, SportsPlayerBoxscore.game_id == db_models.SportsGame.id)
        .where(db_models.SportsGame.id.in_(game_ids))
        .where(func.lower(SportsPlayerBoxscore.player_name).like(f"%{player.lower()}%"))
        .order_by(db_models.SportsGame.game_date)
    )
    res = await session.execute(stmt)
    rows = res.fetchall()
    minutes_map: dict[int, dict[str, float | None]] = {}
    history: list[float] = []
    for gid, game_date, stats in rows:
        mins_val = stats.get("minutes") or stats.get("mp")
        try:
            minutes_float = float(mins_val) if mins_val is not None else None
        except (TypeError, ValueError):
            minutes_float = None
        rolling = None
        if history:
            rolling = float(statistics.mean(history[-window:]))
        delta = None
        if minutes_float is not None and rolling is not None:
            delta = minutes_float - rolling
        minutes_map[gid] = {
            "player_minutes": minutes_float,
            "player_minutes_rolling": rolling,
            "player_minutes_delta": delta,
        }
        if minutes_float is not None:
            history.append(minutes_float)
    return minutes_map


def _attach_player_minutes(feature_data: list[dict[str, Any]], minutes_map: dict[int, dict[str, float | None]]) -> None:
    if not minutes_map:
        return
    for row in feature_data:
        gid = row.get("game_id")
        if gid in minutes_map:
            row.update(minutes_map[gid])
