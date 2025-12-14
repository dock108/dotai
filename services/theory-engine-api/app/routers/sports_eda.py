"""Admin EDA endpoints for sports data.

These endpoints power internal exploratory analysis and will eventually
serve as the backbone modeling interface for matchup evaluation and
simulations. They are **admin-only** and are not exposed to end users.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
import csv
import io
import os
from typing import Any
import statistics

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Select, func, select, text, and_, or_
from sqlalchemy.orm import selectinload, aliased

from .. import db_models
from ..db import AsyncSession, get_db
import numpy as np

from engine.common.feature_layers import build_combined_feature_builder  # type: ignore

from ..services.derived_metrics import compute_derived_metrics
from ..services.feature_compute import compute_features_for_games
from ..services.feature_engine import generate_features, summarize_features
from ..services.model_builder import predict_proba, train_logistic_regression
from ..services.theory_generator import generate_theories
from ..services.eda.targeting import resolve_target_definition, target_value
from ..services.eda.feature_policy import feature_policy_report
from ..services.eda.pruning import prune_feature_matrix
from ..services.eda.exposure import apply_exposure_controls, build_bet_tape
from ..services.eda.slicing import slice_metrics, build_performance_slices, build_failure_analysis
from ..services.eda.mc_text import mc_assumptions_payload, mc_interpretation_lines
from ..services.eda.theory_candidates import generate_theory_candidates
from ..services.eda.micro_store import save_run
import structlog
from ..services.historical_mc import simulate_historical_mc
from ..utils.odds import implied_probability_from_american, profit_for_american_odds
from ..db_models import SportsPlayerBoxscore
from ..services.feature_metadata import FeatureTiming, FeatureSource, get_feature_metadata  # noqa: F401
from .sports_eda_schemas import (
    FeatureGenerationRequest,
    GeneratedFeature,
    FeatureGenerationResponse,
    CleaningOptions,
    CleaningSummary,
    FeatureQualityStats,
    FeaturePreviewSummary,
    FeaturePreviewRequest,
    AnalysisRequest,
    CorrelationResult,
    AnalysisResponse,
    ModelBuildRequest,
    MicroModelRow,
    TheoryMetrics,
    TheoryEvaluation,
    MetaInfo,
    TheoryDescriptor,
    CohortInfo,
    ModelingStatus,
    MonteCarloStatus,
    TrainedModelResponse,
    SuggestedTheoryResponse,
    AnalysisWithMicroResponse,
    ModelBuildWithMicroResponse,
    TargetDefinition,
    TriggerDefinition,
    ExposureControls,
)

MAX_GAMES_LIMIT = 5000
MC_MIN_ODDS_EVENTS = int(os.getenv("MC_MIN_ODDS_EVENTS", "1"))

router = APIRouter(prefix="/api/admin/sports/eda", tags=["sports-eda"])
logger = structlog.get_logger("sports-eda")
# ---------- Feature generation ----------

def _resolve_target_definition(target_def: TargetDefinition | None) -> TargetDefinition:
    if isinstance(target_def, TargetDefinition):
        return target_def
    td_dict = resolve_target_definition(target_def)
    return TargetDefinition(**td_dict)


def _target_value(metrics: dict[str, Any], target_def: TargetDefinition) -> float | str | None:
    return target_value(metrics, target_def.model_dump() if hasattr(target_def, "model_dump") else target_def)


def _feature_policy_report(features: list[GeneratedFeature], context: str) -> tuple[list[GeneratedFeature], dict[str, Any]]:
    return feature_policy_report(features, context)


def _prune_feature_matrix(
    aligned_features: dict[str, list[float]],
    feature_names: list[str],
    *,
    near_zero_weight_eps: float = 1e-6,
    collinearity_threshold: float = 0.98,
    max_features_for_collinearity: int = 600,
) -> tuple[list[str], list[dict[str, Any]]]:
    return prune_feature_matrix(
        aligned_features,
        feature_names,
        near_zero_weight_eps=near_zero_weight_eps,
        collinearity_threshold=collinearity_threshold,
        max_features_for_collinearity=max_features_for_collinearity,
    )

def _apply_exposure_controls(
    micro_rows: list[MicroModelRow],
    *,
    controls: ExposureControls | None,
    target_def: TargetDefinition,
) -> tuple[list[MicroModelRow], dict[str, Any], list[dict[str, Any]]]:
    return apply_exposure_controls(micro_rows, controls=controls, target_def=target_def)


def _build_bet_tape(selected: list[MicroModelRow]) -> list[dict[str, Any]]:
    return build_bet_tape(selected)


def _slice_metrics(rows: list[MicroModelRow]) -> dict[str, Any]:
    return slice_metrics(rows)


def _build_performance_slices(selected_bets: list[MicroModelRow], target_def: TargetDefinition) -> dict[str, Any]:
    return build_performance_slices(selected_bets, target_def=target_def)


def _build_failure_analysis(selected_bets: list[MicroModelRow]) -> dict[str, Any]:
    return build_failure_analysis(selected_bets)


def _mc_assumptions_payload(target_def: TargetDefinition, exposure: dict[str, Any] | None) -> dict[str, Any]:
    return mc_assumptions_payload(target_def.model_dump() if hasattr(target_def, "model_dump") else target_def, exposure)


def _mc_interpretation_lines(mc_summary: dict[str, Any] | None, exposure: dict[str, Any] | None) -> list[str]:
    return mc_interpretation_lines(mc_summary, exposure)


def _generate_theory_candidates(
    aligned_rows: list[dict[str, float]],
    feature_names: list[str],
    *,
    baseline_rate: float,
    target_def: TargetDefinition,
    min_sample_size: int = 150,
    min_lift: float = 0.02,
) -> list[dict[str, Any]]:
    td_dict = target_def.model_dump() if hasattr(target_def, "model_dump") else target_def
    return generate_theory_candidates(
        aligned_rows,
        feature_names,
        baseline_rate=baseline_rate,
        target_def=td_dict,
        min_sample_size=min_sample_size,
        min_lift=min_lift,
    )


def _snapshot_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _build_model_snapshot(
    *,
    req: ModelBuildRequest,
    target_def: TargetDefinition,
    policy: dict[str, Any],
    dropped_features: list[dict[str, Any]] | None,
    features_used: list[str],
    trigger_def: TriggerDefinition | None,
    exposure_controls: ExposureControls | None,
) -> dict[str, Any]:
    payload = {
        "version": 1,
        "created_at": datetime.utcnow().isoformat(),
        "league_code": req.league_code,
        "filters": {
            "seasons": req.seasons,
            "phase": req.phase,
            "recent_days": req.recent_days,
            "team": req.team,
            "player": req.player,
            "home_spread_min": req.home_spread_min,
            "home_spread_max": req.home_spread_max,
        },
        "context": req.context,
        "target_definition": target_def.model_dump() if hasattr(target_def, "model_dump") else target_def.dict(),
        "trigger_definition": (trigger_def.model_dump() if (trigger_def and hasattr(trigger_def, "model_dump")) else (trigger_def.dict() if trigger_def else None)),
        "exposure_controls": (
            exposure_controls.model_dump()
            if (exposure_controls and hasattr(exposure_controls, "model_dump"))
            else (exposure_controls.dict() if exposure_controls else None)
        ),
        "cleaning": (req.cleaning.model_dump() if (req.cleaning and hasattr(req.cleaning, "model_dump")) else (req.cleaning.dict() if req.cleaning else None)),
        "features_requested": [f.name for f in req.features],
        "feature_policy": policy,
        "features_used": features_used,
        "features_dropped": dropped_features or [],
    }
    return {"hash": _snapshot_hash(payload), "payload": payload}


async def _get_league(session: AsyncSession, code: str) -> db_models.SportsLeague:
    stmt = select(db_models.SportsLeague).where(db_models.SportsLeague.code == code.upper())
    result = await session.execute(stmt)
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"League {code} not found")
    return league


def _resolve_layer_builder(mode: str | None):
    if not mode:
        return None
    normalized = mode.lower()
    if normalized not in {"admin", "full"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="feature_mode must be 'admin' or 'full'")
    return build_combined_feature_builder(normalized)


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
    # Phase filter (NCAAB only): out_conf (< Jan 1), conf (Jan 1–Mar 15), postseason (Mar 16+)
    phase = getattr(req, "phase", None)
    phase_ranges = _build_phase_ranges(getattr(league, "code", None), seasons, phase)
    if phase_ranges:
        clauses = [
            and_(db_models.SportsGame.game_date >= start_dt, db_models.SportsGame.game_date < end_dt)
            for start_dt, end_dt in phase_ranges
        ]
        stmt = stmt.where(or_(*clauses))
    # Recent rolling window (from today backwards)
    recent_days = getattr(req, "recent_days", None)
    if recent_days:
        cutoff = datetime.utcnow() - timedelta(days=recent_days)
        stmt = stmt.where(db_models.SportsGame.game_date >= cutoff)
    # Spread filters (home) - accept any spread line (team-based sides in NCAAB)
    spread_min = getattr(req, "home_spread_min", None)
    spread_max = getattr(req, "home_spread_max", None)
    if spread_min is not None or spread_max is not None:
        stmt = stmt.join(db_models.SportsGameOdds, db_models.SportsGameOdds.game_id == db_models.SportsGame.id)
        stmt = stmt.where(db_models.SportsGameOdds.market_type == "spread")
        if spread_min is not None:
            stmt = stmt.where(db_models.SportsGameOdds.line >= spread_min)
        if spread_max is not None:
            stmt = stmt.where(db_models.SportsGameOdds.line <= spread_max)
    # Team filter
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


def _build_phase_ranges(league_code: str | None, seasons: list[int] | None, phase: str | None):
    """
    Build date ranges for NCAAB phases aligned to season timing:
    - Season runs roughly Nov 1 (season year) through Apr 15 (next year).
    - out_conf: Nov 1 -> Jan 1
    - conf: Jan 1 -> Mar 16
    - postseason: Mar 16 -> Apr 16
    """
    if not league_code or league_code.upper() != "NCAAB":
        return None
    if not seasons or not phase or phase == "all":
        return None
    ranges: list[tuple[datetime, datetime]] = []
    for s in seasons:
        season_start = datetime(s, 11, 1)
        conf_year = s + 1  # Jan/Mar/Apr fall in next calendar year
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
@router.post("/generate-features", response_model=FeatureGenerationResponse)
async def generate_feature_catalog(req: FeatureGenerationRequest) -> FeatureGenerationResponse:
    """Generate feature descriptors based on selected raw stats and context flags."""
    generated = generate_features(
        raw_stats=req.raw_stats,
        include_rest_days=req.include_rest_days,
        include_rolling=req.include_rolling,
        rolling_window=req.rolling_window,
    )
    features = [
        GeneratedFeature(
            name=f.name,
            formula=f.formula,
            category=f.category,
            requires=f.requires,
            timing=getattr(f, "timing", None).value if getattr(f, "timing", None) is not None else None,
            source=getattr(f, "source", None).value if getattr(f, "source", None) is not None else None,
            group=getattr(f, "group", None),
        )
        for f in generated
    ]
    return FeatureGenerationResponse(
        features=features,
        summary=summarize_features(generated, req.raw_stats, req.include_rest_days),
    )
def _target_value_legacy(metrics: dict[str, Any], target: str | None) -> float | None:
    """Back-compat shim for older callers passing target as a string."""
    td = _resolve_target_definition(target)
    return _target_value(metrics, td)


def _pearson_correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) < 5:
        return None
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    if np.std(x_arr) == 0 or np.std(y_arr) == 0:
        return None
    return float(np.corrcoef(x_arr, y_arr)[0, 1])


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
        mean_val = float(np.mean(numeric_values)) if numeric_values else None
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


def _build_micro_rows(
    games: list[db_models.SportsGame],
    feature_data: list[dict[str, Any]],
    kept_ids: list[int],
    target_map: dict[int, float],
    trigger_flag: bool = True,
    target_def: TargetDefinition | None = None,
    model_prob_by_game_id: dict[int, float] | None = None,
    trigger_def: TriggerDefinition | None = None,
) -> list[MicroModelRow]:
    """Construct micro_model_results rows aligned to kept_ids."""
    game_lookup = {g.id: g for g in games}
    rows: list[MicroModelRow] = []
    td = target_def
    trig = trigger_def or TriggerDefinition()
    for row in feature_data:
        gid = row.get("game_id")
        if gid not in kept_ids:
            continue
        game = game_lookup.get(gid)
        metrics = compute_derived_metrics(game, game.odds or []) if game else {}
        closing_line: float | None = None
        closing_odds: float | None = None
        if td and td.market_type == "spread":
            closing_line = metrics.get("closing_spread_home") if td.side == "home" else metrics.get("closing_spread_away")
            closing_odds = metrics.get("closing_spread_home_price") if td.side == "home" else metrics.get("closing_spread_away_price")
        elif td and td.market_type == "total":
            closing_line = metrics.get("closing_total")
            closing_odds = metrics.get("closing_total_price")
        elif td and td.market_type == "moneyline":
            closing_odds = metrics.get("closing_ml_home") if td.side == "home" else metrics.get("closing_ml_away")

        odds_for_math = closing_odds
        implied_prob = implied_probability_from_american(float(odds_for_math)) if odds_for_math is not None else None
        tgt = target_map.get(gid)
        is_market = bool(td and td.target_class == "market")

        # Derive outcome context from stats regardless of target class
        winner = metrics.get("winner")
        total_result = metrics.get("total_result")  # "over" | "under" | None

        if is_market:
            outcome = "win" if tgt == 1 else "loss" if tgt == 0 else "push"
            if outcome == "win" and odds_for_math is not None:
                pnl = profit_for_american_odds(float(odds_for_math), risk_units=1.0)
            elif outcome == "loss":
                pnl = -1.0
            else:
                pnl = 0.0
        else:
            # Stat targets: keep pnl neutral but still communicate game result
            pnl = 0.0
            outcome = None
            if td:
                if td.target_name == "combined_score":
                    outcome = total_result if total_result in ("over", "under") else "push"
                elif td.target_name == "winner":
                    outcome = winner if winner in ("home", "away") else None
                elif td.target_name in ("margin_of_victory", "home_points", "away_points"):
                    outcome = winner if winner in ("home", "away") else None
        model_prob = (model_prob_by_game_id or {}).get(gid)
        edge_vs_implied = (model_prob - implied_prob) if (model_prob is not None and implied_prob is not None) else None

        # Stage 2.1 trigger evaluation (truthful: if missing model_prob/implied_prob, we can't trigger)
        reasons: list[str] = []
        did_trigger = bool(trigger_flag)
        if not is_market:
            # Stat targets: disable triggering and EV/edge; model_prob not meaningful here
            did_trigger = False
            model_prob = None
            edge_vs_implied = None
            reasons.append("stat target: triggers disabled")
        else:
            if model_prob is None:
                did_trigger = False
                reasons.append("missing model probability")
            if implied_prob is None:
                did_trigger = False
                reasons.append("missing implied probability (odds)")
            if model_prob is not None:
                if model_prob < trig.prob_threshold:
                    did_trigger = False
                    reasons.append(f"model_prob {model_prob:.3f} < threshold {trig.prob_threshold:.3f}")
                if trig.confidence_band is not None and abs(model_prob - 0.5) < trig.confidence_band:
                    did_trigger = False
                    reasons.append(f"confidence |p-0.5| {abs(model_prob-0.5):.3f} < band {trig.confidence_band:.3f}")
            if edge_vs_implied is not None and trig.min_edge_vs_implied is not None and edge_vs_implied < trig.min_edge_vs_implied:
                did_trigger = False
                reasons.append(f"edge {edge_vs_implied:.3f} < min_edge {trig.min_edge_vs_implied:.3f}")

        # If it triggers, provide a positive justification line too
        if did_trigger and model_prob is not None:
            reasons.insert(0, f"model_prob {model_prob:.3f} passes trigger")

        ev_pct = None
        rows.append(
            MicroModelRow(
                theory_id=None,
                game_id=gid,
                target_name=td.target_name if td else "",
                target_value=tgt,
                baseline_value=None,
                market_type=td.market_type if td and td.target_class == "market" else None,
                side=td.side if td and td.target_class == "market" else None,
                closing_line=closing_line,
                closing_odds=closing_odds,
                implied_prob=implied_prob,
                model_prob=model_prob,
                edge_vs_implied=edge_vs_implied,
                final_score_home=getattr(game, "home_score", None) if game else None,
                final_score_away=getattr(game, "away_score", None) if game else None,
                outcome=outcome,
                pnl_units=pnl,
                est_ev_pct=ev_pct,
                trigger_flag=did_trigger,
                features={k: v for k, v in row.items() if k != "game_id"},
                meta={
                    "season": getattr(game, "season", None) if game else None,
                    "game_date": getattr(game, "game_date", None).isoformat() if (game and game.game_date) else None,
                    "conference": getattr(game, "is_conference_game", None) if game else None,
                    "target_definition": td.model_dump() if hasattr(td, "model_dump") else td.dict(),
                    "trigger_definition": trig.model_dump() if hasattr(trig, "model_dump") else trig.dict(),
                    "trigger_reasons": reasons,
                },
            )
        )
    return rows


def _compute_theory_metrics(rows: list[MicroModelRow], target_def: TargetDefinition, baseline_rows: list[MicroModelRow] | None = None) -> TheoryMetrics | None:
    """Market metrics only. Stat targets return None to avoid percent semantics."""
    if target_def.target_class == "stat":
        return None

    n = len(rows)
    eval_rows = [r for r in rows if r.outcome in {"win", "loss"}]
    n_eval = len(eval_rows)
    cover_rate = sum(1 for r in eval_rows if r.outcome == "win") / n_eval if n_eval else 0.0
    base_rate = None
    if baseline_rows:
        b_rows = [r for r in baseline_rows if r.outcome in {"win", "loss"}]
        b = len(b_rows)
        base_rate = sum(1 for r in b_rows if r.outcome == "win") / b if b else None
    delta = (cover_rate - base_rate) if base_rate is not None else None
    implied = [r.implied_prob for r in eval_rows if r.implied_prob is not None]
    ev_vs_implied = ((cover_rate - float(np.mean(implied))) * 100.0) if implied else None
    pnl_curve: list[float] = []
    acc = 0.0
    for r in eval_rows:
        acc += r.pnl_units or 0.0
        pnl_curve.append(acc)
    max_dd = None
    peak = -1e9
    for v in pnl_curve:
        peak = max(peak, v)
        dd = peak - v
        max_dd = dd if max_dd is None or dd > max_dd else max_dd
    sharpe_like = None
    pnl_changes = [r.pnl_units for r in eval_rows if r.pnl_units is not None]
    if len(pnl_changes) > 1:
        sharpe_like = float(np.mean(pnl_changes) / (np.std(pnl_changes) + 1e-9))
    time_stability = None
    return TheoryMetrics(
        sample_size=n,
        cover_rate=cover_rate,
        baseline_cover_rate=base_rate,
        delta_cover=delta,
        ev_vs_implied=ev_vs_implied,
        sharpe_like=sharpe_like,
        max_drawdown=max_dd,
        time_stability=time_stability,
    )


def _compute_theory_evaluation(rows: list[MicroModelRow], target_def: TargetDefinition) -> TheoryEvaluation | None:
    """Lightweight evaluation that does not require modeling."""
    if not rows:
        return None

    if target_def.target_class == "stat":
        values: list[float] = []
        stability: dict[str, list[float]] = {}
        for r in rows:
            if isinstance(r.target_value, (int, float)):
                values.append(float(r.target_value))
                season = (r.meta or {}).get("season")
                if season is not None:
                    stability.setdefault(str(season), []).append(float(r.target_value))
        if not values:
            return None
        cohort = float(np.mean(values))
        baseline = cohort  # using cohort mean as baseline fallback; avoids misleading "rate" semantics
        delta = cohort - baseline if baseline is not None else None
        stability_mean = {k: float(np.mean(v)) for k, v in stability.items() if v}
        verdict = None
        if delta is not None:
            if abs(delta) >= 5:
                verdict = "interesting"
            elif abs(delta) >= 2:
                verdict = "weak"
            else:
                verdict = "noise"
        return TheoryEvaluation(
            target_class="stat",
            sample_size=len(values),
            cohort_value=cohort,
            baseline_value=baseline,
            delta_value=delta,
            formatting="numeric",
            notes=["Observational theory — no betting simulation."],
            stability_by_season=stability_mean or None,
            verdict=verdict,
        )

    # market target
    eval_rows = [r for r in rows if r.outcome in {"win", "loss"}]
    n_eval = len(eval_rows)
    if n_eval == 0:
        return None
    cover_rate = sum(1 for r in eval_rows if r.outcome == "win") / n_eval
    implied = [r.implied_prob for r in eval_rows if r.implied_prob is not None]
    baseline = float(np.mean(implied)) if implied else None
    delta = (cover_rate - baseline) if baseline is not None else None
    verdict = None
    if delta is not None:
        if delta >= 0.03:
            verdict = "interesting"
        elif delta >= 0.01:
            verdict = "weak"
        else:
            verdict = "noise"
    return TheoryEvaluation(
        target_class="market",
        sample_size=n_eval,
        cohort_value=cover_rate,
        baseline_value=baseline,
        delta_value=delta,
        formatting="percent",
        notes=None,
        stability_by_season=None,
        verdict=verdict,
    )


def _build_meta(run_id: str) -> MetaInfo:
    return MetaInfo(
        run_id=run_id,
        snapshot_hash=None,
        created_at=datetime.utcnow(),
        engine_version=os.environ.get("ENGINE_VERSION"),
    )


def _build_theory_descriptor(target_def: TargetDefinition, filters: dict[str, Any]) -> TheoryDescriptor:
    return TheoryDescriptor(
        target=target_def.model_dump(),
        filters=filters,
    )


def _build_cohort(sample_size: int, target_def: TargetDefinition) -> CohortInfo:
    baseline_type = "stat_mean" if target_def.target_class == "stat" else "implied_prob"
    baseline_desc = "Mean of target values" if target_def.target_class == "stat" else "Average implied probability from odds"
    return CohortInfo(
        sample_size=sample_size,
        time_span=None,
        baseline_definition={"type": baseline_type, "description": baseline_desc},
    )


def _mc_eligibility(rows: list[MicroModelRow], target_def: TargetDefinition) -> tuple[bool, str | None]:
    if target_def.target_class != "market":
        return False, "stat_target_no_mc"
    odds_count = sum(1 for r in rows if r.closing_odds is not None)
    if odds_count >= MC_MIN_ODDS_EVENTS:
        return True, None
    return False, "missing_odds"


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


@router.post("/preview")
async def preview_features(req: FeaturePreviewRequest, session: AsyncSession = Depends(get_db)):
    """Preview feature matrix before running analysis. Supports CSV or JSON quality summary."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    filtered_features, _policy = _feature_policy_report(req.features, req.context)

    stmt: Select = select(db_models.SportsGame.id)
    stmt = _apply_base_filters(stmt, league, req)
    if req.offset is not None:
        stmt = stmt.offset(req.offset)
    if req.limit is not None:
        stmt = stmt.limit(req.limit)
    game_rows = await session.execute(stmt)
    all_game_ids = [row[0] for row in game_rows.fetchall()]
    all_game_ids = await _filter_games_by_player(session, all_game_ids, getattr(req, "player", None))

    if not all_game_ids:
        if req.format.lower() == "json":
            return FeaturePreviewSummary(rows_inspected=0, feature_stats={})
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["game_id", *[f.name for f in filtered_features]])
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )
    minutes_map = await _player_minutes_map(session, all_game_ids, getattr(req, "player", None))
    _attach_player_minutes(feature_data, minutes_map)
    feature_names = [f.name for f in filtered_features if (not req.feature_filter or f.name in req.feature_filter)]

    fmt = req.format.lower()
    if fmt == "json":
        filtered_data = [
            {k: v for k, v in row.items() if (k == "game_id" or k in feature_names)} for row in feature_data
        ]
        stats = _compute_quality_stats(filtered_data, feature_names)
        items = list(stats.items())
        sort_by = (req.sort_by or "null_pct").lower()
        sort_dir = (req.sort_dir or "desc").lower()
        reverse = sort_dir != "asc"
        if sort_by == "non_numeric":
            items.sort(key=lambda kv: kv[1].non_numeric, reverse=reverse)
        elif sort_by == "name":
            items.sort(key=lambda kv: kv[0], reverse=reverse)
        else:
            items.sort(key=lambda kv: kv[1].null_pct, reverse=reverse)
        stats = {k: v for k, v in items}
        return FeaturePreviewSummary(rows_inspected=len(filtered_data), feature_stats=stats)

    # CSV path
    include_target = bool(req.include_target)
    game_to_targets: dict[int, float] = {}
    if include_target:
        td = _resolve_target_definition(req.target_definition)
        stmt_games = select(db_models.SportsGame).where(db_models.SportsGame.id.in_(all_game_ids)).options(
            selectinload(db_models.SportsGame.odds),
            selectinload(db_models.SportsGame.home_team),
            selectinload(db_models.SportsGame.away_team),
        )
        games_res = await session.execute(stmt_games)
        for game in games_res.scalars().all():
            metrics = compute_derived_metrics(game, game.odds)
            tgt_val = _target_value(metrics, td)
            if tgt_val is not None:
                game_to_targets[game.id] = tgt_val

    header = ["game_id"]
    if include_target:
        header.append("target")
    header.extend(feature_names)

    def csv_iter():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for row in feature_data:
            gid = row.get("game_id")
            vals = [row.get(fname, "") for fname in feature_names]
            if include_target:
                tgt = game_to_targets.get(gid, "")
                writer.writerow([gid, tgt, *vals])
            else:
                writer.writerow([gid, *vals])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(csv_iter(), media_type="text/csv")


@router.post("/analyze", response_model=AnalysisWithMicroResponse)
async def run_analysis(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> AnalysisWithMicroResponse:
    """Run correlation analysis for generated features against a target."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    target_def = _resolve_target_definition(req.target_definition)
    is_stat = target_def.target_class == "stat"
    filtered_features, policy = feature_policy_report(req.features, req.context)
    if is_stat:
        filtered_features = [
            f
            for f in filtered_features
            if getattr(f, "source", None) != FeatureSource.MARKET and getattr(f, "timing", None) != FeatureTiming.MARKET_DERIVED
        ]

    logger.info(
        "analyze_start",
        league=req.league_code,
        seasons=req.seasons,
        phase=req.phase,
        recent_days=req.recent_days,
        home_spread_min=req.home_spread_min,
        home_spread_max=req.home_spread_max,
        feature_mode=req.feature_mode,
        team=req.team,
        player=req.player,
    )

    # Fetch game ids filtered by seasons if provided
    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    if req.games_limit:
        stmt = stmt.limit(min(req.games_limit, MAX_GAMES_LIMIT))
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]
    all_game_ids = await _filter_games_by_player(session, all_game_ids, getattr(req, "player", None))
    games = [g for g in games if g.id in all_game_ids]

    logger.info(
        "analyze_games_filtered",
        game_count=len(all_game_ids),
        sample_ids=all_game_ids[:20],
    )

    if not all_game_ids:
        return AnalysisResponse(
            sample_size=0,
            baseline_rate=0.0,
            correlations=[],
            best_segments=[],
            insights=["No games found for the selected filters."],
            feature_policy=policy,
        )

    # Compute feature values
    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )
    logger.info(
        "analyze_features_ready",
        game_count=len(all_game_ids),
        feature_count=len(filtered_features),
    )

    # Fetch derived targets
    game_to_targets: dict[int, float] = {}
    stmt_games = (
        select(db_models.SportsGame)
        .where(db_models.SportsGame.id.in_(all_game_ids))
        .options(
            selectinload(db_models.SportsGame.odds),
            selectinload(db_models.SportsGame.home_team),
            selectinload(db_models.SportsGame.away_team),
        )
    )
    games_res = await session.execute(stmt_games)
    for game in games_res.scalars().all():
        metrics = compute_derived_metrics(game, game.odds)
        tgt_val = _target_value(metrics, target_def)
        if tgt_val is not None:
            game_to_targets[game.id] = tgt_val

    # Assemble aligned data
    feature_names = [f.name for f in filtered_features]
    aligned_features, aligned_target, kept_ids, cleaning_summary = _prepare_dataset(
        feature_data, feature_names, game_to_targets, req.cleaning
    )
    sample_size = len(aligned_target)
    if sample_size == 0:
        try:
            structlog.get_logger("eda_analyze").info(
                "analyze_no_targets",
                games=len(all_game_ids),
                target=f"{target_def.market_type}:{target_def.side}",
            )
        except Exception:
            pass
        return AnalysisResponse(
            sample_size=0,
            baseline_rate=0.0,
            correlations=[],
            best_segments=[],
            insights=["No target values available for selected games."],
            cleaning_summary=cleaning_summary,
            feature_policy=policy,
        )

    baseline_rate = float(np.mean(aligned_target))

    correlations: list[CorrelationResult] = []
    insights: list[str] = []

    # Drop duplicate/identical feature vectors and near-constant features to avoid skew
    usable_features: dict[str, list[float]] = {}
    seen_signatures: set[tuple] = set()
    dropped_dupe = 0
    dropped_low_var = 0
    for name, values in aligned_features.items():
        if len(values) != sample_size:
            continue
        clean_vals = [v for v in values if not np.isnan(v)]
        if len(clean_vals) < 5:
            continue
        if np.std(clean_vals) < 1e-9:  # effectively constant
            dropped_low_var += 1
            continue
        signature = tuple(None if np.isnan(v) else round(float(v), 6) for v in values)
        if signature in seen_signatures:
            dropped_dupe += 1
            continue
        seen_signatures.add(signature)
        usable_features[name] = values

    for name, values in usable_features.items():
        clean_pairs = [(x, y) for x, y in zip(values, aligned_target) if not (np.isnan(x) or np.isnan(y))]
        if len(clean_pairs) < 5:
            continue
        xs = [p[0] for p in clean_pairs]
        ys = [p[1] for p in clean_pairs]
        corr = _pearson_correlation(xs, ys)
        if corr is None:
            continue
        is_sig = abs(corr) >= 0.05
        correlations.append(CorrelationResult(feature=name, correlation=corr, p_value=None, is_significant=is_sig))
        if is_sig:
            direction = "more" if corr > 0 else "less"
            label = f"{target_def.market_type}:{target_def.side}"
            insights.append(f"{name} correlates with {label}: {direction} {label} when this increases.")

    correlations = sorted(correlations, key=lambda c: abs(c.correlation), reverse=True)[:10]

    insights_out = insights[:5]
    if not insights_out:
        insights_out = ["No strong correlations detected."]
        if dropped_dupe or dropped_low_var:
            insights_out.append(
                f"Dropped {dropped_dupe} duplicate feature vectors and {dropped_low_var} low-variance features."
            )

    micro_rows = _build_micro_rows(games, feature_data, kept_ids, game_to_targets, trigger_flag=True, target_def=target_def)
    theory_metrics = _compute_theory_metrics(micro_rows, target_def, None)
    theory_evaluation = _compute_theory_evaluation(micro_rows, target_def)
    odds_present = any(r.closing_odds is not None for r in micro_rows)
    mc_ok, mc_reason = _mc_eligibility(micro_rows, target_def)
    modeling_status = ModelingStatus(
        available=True,
        has_run=False,
        reason_not_run="user_has_not_requested",
        eligibility={"sufficient_features": len(filtered_features) > 0, "target_supported": True},
        model_type=None,
        metrics=None,
        feature_importance=None,
    )
    monte_carlo_status = MonteCarloStatus(
        available=mc_ok,
        has_run=False,
        reason_not_run="user_has_not_requested" if mc_ok else None,
        reason_not_available=mc_reason if not mc_ok else None,
        eligibility={"odds_present": odds_present, "min_events": MC_MIN_ODDS_EVENTS} if mc_ok else None,
        results=None,
    )
    notes = [
        "Theory evaluation is complete without modeling.",
        "Modeling and Monte Carlo are optional analytical extensions.",
        "This theory does not require market simulation to be valid.",
    ]
    filters_payload = {
        "seasons": req.seasons,
        "phase": req.phase,
        "recent_days": req.recent_days,
        "home_spread_min": req.home_spread_min,
        "home_spread_max": req.home_spread_max,
        "team": req.team,
        "player": req.player,
        "feature_mode": req.feature_mode,
    }
    run_id = hashlib.sha256(json.dumps({"target": target_def.model_dump(), "filters": all_game_ids}).encode()).hexdigest()
    try:
        save_run(
            run_id,
            {
                "target": target_def.model_dump(),
                "game_ids": all_game_ids,
                "micro_rows": [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in micro_rows],
            },
        )
    except Exception:
        pass

    logger.info(
        "analyze_done",
        sample_size=sample_size,
        baseline_rate=baseline_rate,
        micro_rows=len(micro_rows),
    )
    return AnalysisWithMicroResponse(
        sample_size=sample_size,
        baseline_rate=baseline_rate,
        correlations=correlations,
        best_segments=[],
        insights=insights_out,
        cleaning_summary=cleaning_summary,
        micro_model_results=micro_rows,
        theory_metrics=theory_metrics,
        theory_evaluation=theory_evaluation,
        feature_policy=policy,
        run_id=run_id,
        meta=_build_meta(run_id),
        theory=_build_theory_descriptor(target_def, filters_payload),
        cohort=_build_cohort(sample_size, target_def),
        modeling=modeling_status,
        monte_carlo=monte_carlo_status,
        notes=notes,
    )
# End of file


# EOF

# EOF
@router.post("/analyze/export")
async def export_analysis_csv(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Export the feature matrix with targets as CSV, for the same filters/features/target used in analysis."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    filtered_features, _policy = _feature_policy_report(req.features, req.context)
    target_def = _resolve_target_definition(req.target_definition)

    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    if req.games_limit:
        stmt = stmt.limit(req.games_limit)
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]
    all_game_ids = await _filter_games_by_player(session, all_game_ids, getattr(req, "player", None))
    games = [g for g in games if g.id in all_game_ids]

    if not all_game_ids:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["game_id", "target", *[f.name for f in filtered_features]])
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )

    # Fetch derived targets
    game_to_targets: dict[int, float] = {}
    stmt_games = select(db_models.SportsGame).where(db_models.SportsGame.id.in_(all_game_ids)).options(
        selectinload(db_models.SportsGame.odds),
        selectinload(db_models.SportsGame.home_team),
        selectinload(db_models.SportsGame.away_team),
    )
    games_res = await session.execute(stmt_games)
    for game in games_res.scalars().all():
        metrics = compute_derived_metrics(game, game.odds)
        tgt_val = _target_value(metrics, target_def)
        if tgt_val is not None:
            game_to_targets[game.id] = tgt_val

    feature_names = [f.name for f in filtered_features]
    aligned_features, aligned_target, kept_ids, _summary = _prepare_dataset(
        feature_data, feature_names, game_to_targets, req.cleaning
    )

    def csv_iter():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["game_id", "target", *feature_names])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for idx, gid in enumerate(kept_ids):
            row_vals = []
            for fname in feature_names:
                val = aligned_features[fname][idx]
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    row_vals.append("")
                else:
                    row_vals.append(val)
            writer.writerow([gid, aligned_target[idx], *row_vals])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(csv_iter(), media_type="text/csv")


@router.post("/micro-model/export")
async def export_micro_model(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Export per-game micro_model_results CSV for given filters/features/target."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    filtered_features, _policy = _feature_policy_report(req.features, req.context)
    target_def = _resolve_target_definition(req.target_definition)

    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    if req.games_limit:
        stmt = stmt.limit(req.games_limit)
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )

    # targets
    game_to_targets: dict[int, float] = {}
    for game in games:
        metrics = compute_derived_metrics(game, game.odds)
        tgt_val = _target_value(metrics, target_def)
        if tgt_val is not None:
            game_to_targets[game.id] = tgt_val

    feature_names = [f.name for f in filtered_features]
    aligned_features, aligned_target, kept_ids, _summary = _prepare_dataset(
        feature_data, feature_names, game_to_targets, req.cleaning
    )
    micro_rows = _build_micro_rows(games, feature_data, kept_ids, game_to_targets, trigger_flag=True, target_def=target_def)

    def csv_iter():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "theory_id",
                "game_id",
                "market_type",
                "side",
                "closing_line",
                "closing_odds",
                "implied_prob",
                "final_score_home",
                "final_score_away",
                "outcome",
                "pnl_units",
                "est_ev_pct",
                "trigger_flag",
                *feature_names,
            ]
        )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for idx, mm in enumerate(micro_rows):
            feature_vals = []
            for fname in feature_names:
                feature_vals.append((mm.features or {}).get(fname, ""))
            writer.writerow(
                [
                    mm.theory_id or "",
                    mm.game_id,
                    mm.market_type,
                    mm.side,
                    mm.closing_line or "",
                    mm.closing_odds or "",
                    mm.implied_prob or "",
                    mm.final_score_home or "",
                    mm.final_score_away or "",
                    mm.outcome or "",
                    mm.pnl_units or "",
                    mm.est_ev_pct or "",
                    mm.trigger_flag,
                    *feature_vals,
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(csv_iter(), media_type="text/csv")


@router.post("/build-model", response_model=ModelBuildWithMicroResponse)
async def build_model(req: ModelBuildRequest, session: AsyncSession = Depends(get_db)) -> ModelBuildWithMicroResponse:
    """Train a lightweight model on the computed features and return suggested theories."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    target_def = _resolve_target_definition(req.target_definition)
    is_stat = target_def.target_class == "stat"
    filtered_features, policy = _feature_policy_report(req.features, req.context)
    if is_stat:
        filtered_features = [
            f
            for f in filtered_features
            if getattr(f, "source", None) != FeatureSource.MARKET and getattr(f, "timing", None) != FeatureTiming.MARKET_DERIVED
        ]
    logger.info(
        "build_model_start",
        league=req.league_code,
        seasons=req.seasons,
        phase=req.phase,
        recent_days=req.recent_days,
        feature_mode=req.feature_mode,
        target=target_def.target_name,
    )

    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]
    logger.info("build_model_filtered", game_count=len(all_game_ids), sample_ids=all_game_ids[:20])

    if not all_game_ids:
        return ModelBuildWithMicroResponse(
            model_summary=TrainedModelResponse(
                model_type="logistic_regression",
                features_used=[],
                feature_weights={},
                accuracy=0.0,
                roi=0.0,
            ),
            suggested_theories=[],
            validation_stats={},
            feature_policy=policy,
        )

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )
    logger.info(
        "build_model_features_ready",
        game_count=len(all_game_ids),
        feature_count=len(filtered_features),
    )

    # target values
    stmt_games = (
        select(db_models.SportsGame)
        .where(db_models.SportsGame.id.in_(all_game_ids))
        .options(
            selectinload(db_models.SportsGame.odds),
            selectinload(db_models.SportsGame.home_team),
            selectinload(db_models.SportsGame.away_team),
        )
    )
    games_res = await session.execute(stmt_games)
    game_to_target: dict[int, float] = {}
    for game in games_res.scalars().all():
        metrics = compute_derived_metrics(game, game.odds)
        tgt_val = _target_value(metrics, target_def)
        if tgt_val is not None:
            game_to_target[game.id] = tgt_val

    feature_names = [f.name for f in filtered_features]
    aligned_features, aligned_target, kept_ids, cleaning_summary = _prepare_dataset(
        feature_data, feature_names, game_to_target, req.cleaning
    )

    # Stage 1.3: redundancy pruning before training
    pruned_features, dropped_log = _prune_feature_matrix(aligned_features, feature_names)

    aligned_rows: list[dict[str, float]] = []
    for idx in range(len(aligned_target)):
        entry: dict[str, float] = {"__target__": aligned_target[idx]}
        for fname in pruned_features:
            val = aligned_features[fname][idx]
            entry[fname] = 0.0 if (val is None or np.isnan(val)) else float(val)
        aligned_rows.append(entry)

    trained = train_logistic_regression(aligned_rows, pruned_features, "__target__") if not is_stat else None

    # Stage 1.3: drop near-zero weight features (post-training)
    if trained:
        zero_weight = [f for f, w in trained.feature_weights.items() if abs(float(w)) <= 1e-6]
        for f in zero_weight:
            dropped_log.append({"feature": f, "reason": "near_zero_weight", "abs_weight": abs(float(trained.feature_weights[f]))})
        if zero_weight:
            kept_after_weights = [f for f in trained.features_used if f not in set(zero_weight)]
            trained.feature_weights = {k: v for k, v in trained.feature_weights.items() if k in set(kept_after_weights)}
            trained.features_used = kept_after_weights

    # Stage 2.1: compute model probabilities per game id for trigger evaluation
    model_prob_by_game_id: dict[int, float] = {}
    if trained:
        for idx, gid in enumerate(kept_ids):
            # aligned_rows order matches kept_ids
            if idx >= len(aligned_rows):
                break
            model_prob_by_game_id[gid] = float(predict_proba(trained, aligned_rows[idx]))

    # Use previous analysis correlations if available; otherwise empty
    correlations: list[CorrelationResult] = []
    suggested = generate_theories(trained, correlations, [], target_def, len(aligned_rows)) if trained else []

    micro_rows = _build_micro_rows(
        games,
        feature_data,
        kept_ids,
        game_to_target,
        trigger_flag=True,
        target_def=target_def,
        model_prob_by_game_id=model_prob_by_game_id,
        trigger_def=req.trigger_definition,
    )
    theory_metrics = _compute_theory_metrics(micro_rows, target_def, None)
    theory_evaluation = _compute_theory_evaluation(micro_rows, target_def)
    mc_ok, mc_reason = _mc_eligibility(micro_rows, target_def)
    mc_summary = simulate_historical_mc(micro_rows) if mc_ok else None
    logger.info(
        "build_model_trained",
        sample_size=len(aligned_rows),
        features_used=len(trained.features_used) if trained else len(pruned_features),
    )
    mc_runs = mc_summary.get("runs") if isinstance(mc_summary, dict) else getattr(mc_summary, "runs", None) if mc_summary else None
    logger.info("build_model_mc_done", runs=mc_runs)
    selected_bets, exposure_summary, dropped_bets_log = _apply_exposure_controls(
        micro_rows, controls=req.exposure_controls, target_def=target_def
    )
    bet_tape = _build_bet_tape(selected_bets)
    performance_slices = _build_performance_slices(selected_bets, target_def=target_def)
    failure_analysis = _build_failure_analysis(selected_bets)
    mc_assumptions = _mc_assumptions_payload(target_def, exposure_summary)
    mc_interpretation = _mc_interpretation_lines(mc_summary, exposure_summary)

    # Stage 5: theory candidates (read-only; user approves in UI)
    baseline_rate = float(np.mean(aligned_target)) if aligned_target else 0.0
    theory_candidates = _generate_theory_candidates(
        aligned_rows,
        trained.features_used if trained else pruned_features,
        baseline_rate=baseline_rate,
        target_def=target_def,
    )
    model_snapshot = _build_model_snapshot(
        req=req,
        target_def=target_def,
        policy=policy,
        dropped_features=dropped_log,
        features_used=trained.features_used if trained else pruned_features,
        trigger_def=req.trigger_definition,
        exposure_controls=req.exposure_controls,
    )

    logger.info(
        "build_model_done",
        sample_size=len(aligned_rows),
        micro_rows=len(micro_rows),
        target=target_def.target_name,
    )
    odds_present = any(r.closing_odds is not None for r in micro_rows)
    modeling_status = ModelingStatus(
        available=True,
        has_run=True,
        reason_not_run=None,
        reason_not_available=None,
        eligibility={"sufficient_features": len(filtered_features) > 0, "target_supported": True},
        model_type=trained.model_type if trained else "stat_descriptive",
        metrics={
            "accuracy": trained.accuracy if trained else None,
            "roi": trained.roi if trained else None,
        },
        feature_importance=[
            {"feature": k, "weight": float(v)}
            for k, v in (trained.feature_weights.items() if trained else {}).items()
        ]
        if trained
        else None,
    )
    monte_carlo_status = MonteCarloStatus(
        available=mc_ok,
        has_run=mc_summary is not None,
        reason_not_run=None if mc_summary is not None or not mc_ok else "user_has_not_requested",
        reason_not_available=mc_reason if not mc_ok else None,
        eligibility={"odds_present": odds_present, "min_events": MC_MIN_ODDS_EVENTS} if mc_ok else None,
        results=mc_summary if mc_summary is None else {**mc_summary, "assumptions": {"bet_sizing": "1u flat", "ordering": "chronological", "independence": True}},
    )
    notes = [
        "Theory evaluation is complete without modeling.",
        "Modeling and Monte Carlo are optional analytical extensions.",
        "This theory does not require market simulation to be valid.",
    ]
    filters_payload = {
        "seasons": req.seasons,
        "phase": req.phase,
        "recent_days": req.recent_days,
        "home_spread_min": req.home_spread_min,
        "home_spread_max": req.home_spread_max,
        "team": req.team,
        "player": req.player,
        "feature_mode": req.feature_mode,
    }

    run_id_build = hashlib.sha256(json.dumps({"target": target_def.model_dump(), "filters": all_game_ids}).encode()).hexdigest()

    return ModelBuildWithMicroResponse(
        model_summary=TrainedModelResponse(
            model_type=trained.model_type if trained else "stat_descriptive",
            features_used=trained.features_used if trained else pruned_features,
            feature_weights=trained.feature_weights if trained else {},
            accuracy=trained.accuracy if trained else 0.0,
            roi=trained.roi if trained else 0.0,
        ),
        suggested_theories=[
          SuggestedTheoryResponse(
              text=t.text,
              features_used=t.features_used,
              historical_edge=t.historical_edge,
              confidence=t.confidence,
          )
          for t in suggested
        ],
        validation_stats={
            "accuracy": trained.accuracy if trained else 0.0,
            "roi": trained.roi if trained else 0.0,
        },
        cleaning_summary=cleaning_summary,
        micro_model_results=micro_rows,
        theory_metrics=theory_metrics,
        mc_summary=mc_summary,
        feature_policy=policy,
        features_dropped=dropped_log,
        exposure_summary={**exposure_summary, "dropped_bets_log": dropped_bets_log[:200]},
        bet_tape=bet_tape,
        performance_slices=performance_slices,
        failure_analysis=failure_analysis,
        mc_assumptions=mc_assumptions,
        mc_interpretation=mc_interpretation,
        theory_candidates=theory_candidates,
        model_snapshot=model_snapshot,
        theory_evaluation=theory_evaluation,
        meta=_build_meta(run_id_build),
        theory=_build_theory_descriptor(target_def, filters_payload),
        cohort=_build_cohort(len(aligned_rows), target_def),
        modeling=modeling_status,
        monte_carlo=monte_carlo_status,
        notes=notes,
    )
# End of file
