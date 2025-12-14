"""Build-model endpoint for EDA."""
from __future__ import annotations

import math
import os
import uuid
from datetime import datetime
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
from fastapi import APIRouter, Depends
from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from .. import db_models
from ..db import AsyncSession, get_db
from ..services.derived_metrics import compute_derived_metrics
from ..services.feature_compute import compute_features_for_games
from ..services.model_builder import predict_proba, train_logistic_regression
from ..services.theory_generator import generate_theories
from ..services.eda.micro_store import save_run
from ..services.historical_mc import simulate_historical_mc
from .sports_eda_helpers import (
    _resolve_layer_builder,
    _get_league,
    _resolve_target_definition,
    _target_value,
    _feature_policy_report,
    _prune_feature_matrix,
    _apply_exposure_controls,
    _build_bet_tape,
    _build_performance_slices,
    _build_failure_analysis,
    _mc_assumptions_payload,
    _mc_interpretation_lines,
    _generate_theory_candidates,
    _build_model_snapshot,
    _build_meta,
    _build_theory_descriptor,
    _build_cohort,
    _mc_eligibility,
    _persist_micro_rows_csv,
)
from .sports_eda_shared import (
    _apply_base_filters,
    _filter_games_by_player,
    _prepare_dataset,
    _drop_target_leakage,
    _build_micro_rows,
    _compute_theory_metrics,
    _compute_theory_evaluation,
)
from .sports_eda_schemas import (
    ModelBuildRequest,
    CorrelationResult,
    ModelingStatus,
    MonteCarloStatus,
    TrainedModelResponse,
    SuggestedTheoryResponse,
    ModelBuildWithMicroResponse,
)

MAX_GAMES_LIMIT = 5000
MC_MIN_ODDS_EVENTS = int(os.getenv("MC_MIN_ODDS_EVENTS", "1"))

router = APIRouter(prefix="/api/admin/sports/eda", tags=["sports-eda"])
logger = structlog.get_logger("sports-eda")


@router.post("/build-model", response_model=ModelBuildWithMicroResponse)
async def build_model(req: ModelBuildRequest, session: AsyncSession = Depends(get_db)) -> ModelBuildWithMicroResponse:
    """Train lightweight model and run MC for market targets."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    target_def = _resolve_target_definition(req.target_definition)
    is_stat = target_def.target_class == "stat"
    filtered_features, policy = _feature_policy_report(req.features, req.context)
    filtered_features = _drop_target_leakage(filtered_features, target_def)

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
    if req.games_limit:
        stmt = stmt.limit(min(req.games_limit, MAX_GAMES_LIMIT))
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]
    all_game_ids = await _filter_games_by_player(session, all_game_ids, getattr(req, "player", None))
    games = [g for g in games if g.id in all_game_ids]

    logger.info("build_model_filtered", game_count=len(all_game_ids), sample_ids=all_game_ids[:20])

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )
    logger.info("build_model_features_ready", game_count=len(all_game_ids), feature_count=len(filtered_features))

    game_to_target: dict[int, float] = {}
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
            game_to_target[game.id] = tgt_val

    feature_names = [f.name for f in filtered_features]
    aligned_features, aligned_target, kept_ids, cleaning_summary = _prepare_dataset(
        feature_data, feature_names, game_to_target, req.cleaning
    )

    pruned_features, dropped_log = _prune_feature_matrix(aligned_features, feature_names)

    aligned_rows: list[dict[str, float]] = []
    for idx in range(len(aligned_target)):
        entry: dict[str, float] = {"__target__": aligned_target[idx]}
        for fname in pruned_features:
            val = aligned_features[fname][idx]
            entry[fname] = 0.0 if (val is None or np.isnan(val)) else float(val)
        aligned_rows.append(entry)

    trained = train_logistic_regression(aligned_rows, pruned_features, "__target__") if not is_stat else None

    if trained:
        zero_weight = [f for f, w in trained.feature_weights.items() if abs(float(w)) <= 1e-6]
        for f in zero_weight:
            dropped_log.append({"feature": f, "reason": "near_zero_weight", "abs_weight": abs(float(trained.feature_weights[f]))})
        if zero_weight:
            kept_after_weights = [f for f in trained.features_used if f not in set(zero_weight)]
            trained.feature_weights = {k: v for k, v in trained.feature_weights.items() if k in set(kept_after_weights)}
            trained.features_used = kept_after_weights

    model_prob_by_game_id: dict[int, float] = {}
    if trained:
        for idx, gid in enumerate(kept_ids):
            if idx >= len(aligned_rows):
                break
            model_prob_by_game_id[gid] = float(predict_proba(trained, aligned_rows[idx]))

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
    odds_coverage_pct = float(sum(1 for r in micro_rows if r.closing_odds is not None) / len(micro_rows)) if micro_rows else 0.0
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

    baseline_value = _safe_float(float(np.mean(aligned_target))) if aligned_target else 0.0
    if baseline_value is None:
        baseline_value = 0.0
    theory_candidates = _generate_theory_candidates(
        aligned_rows,
        trained.features_used if trained else pruned_features,
        baseline_value=baseline_value,
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
            for k, v in (trained.feature_weights if trained else {}).items()
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

    run_id_build = str(uuid.uuid4())
    micro_rows_ref = _persist_micro_rows_csv(run_id_build, micro_rows)
    try:
        save_run(
            run_id_build,
            {
                "created_at": datetime.utcnow().isoformat(),
                "target": target_def.model_dump(),
                "request": req.model_dump() if hasattr(req, "model_dump") else req.dict(),
                "evaluation": theory_evaluation.model_dump() if theory_evaluation and hasattr(theory_evaluation, "model_dump") else theory_evaluation,
                "modeling": modeling_status.model_dump() if hasattr(modeling_status, "model_dump") else None,
                "monte_carlo": monte_carlo_status.model_dump() if hasattr(monte_carlo_status, "model_dump") else None,
                "mc_summary": mc_summary,
                "model_snapshot": model_snapshot,
                "micro_rows_ref": micro_rows_ref,
                "run_type": "build",
                "snapshot_hash": model_snapshot.get("hash") if isinstance(model_snapshot, dict) else None,
                "cohort_size": len(micro_rows),
            },
        )
    except Exception:
        pass

    return ModelBuildWithMicroResponse(
        model_summary=TrainedModelResponse(
            model_type=trained.model_type if trained else "stat_descriptive",
            features_used=trained.features_used if trained else pruned_features,
            feature_weights=trained.feature_weights if trained else {},
            accuracy=trained.accuracy if trained else 0.0,
            roi=trained.roi if trained else 0.0,
            bias=trained.bias if trained else None,
        ),
        suggested_theories=[
            SuggestedTheoryResponse(
                text=s.text if hasattr(s, "text") else s.get("text", ""),
                features_used=s.features_used if hasattr(s, "features_used") else s.get("features_used", []),
                historical_edge=s.historical_edge if hasattr(s, "historical_edge") else s.get("historical_edge", 0.0),
                confidence=s.confidence if hasattr(s, "confidence") else s.get("confidence", ""),
            )
            for s in (suggested or [])
        ],
        validation_stats={},
        cleaning_summary=cleaning_summary,
        run_id=run_id_build,
        feature_policy=policy,
        features_dropped=dropped_log,
        exposure_summary=exposure_summary,
        bet_tape=bet_tape,
        performance_slices=performance_slices,
        failure_analysis=failure_analysis,
        mc_summary=mc_summary,
        mc_assumptions=mc_assumptions,
        mc_interpretation=mc_interpretation,
        theory_candidates=theory_candidates,
        model_snapshot=model_snapshot,
        micro_rows=micro_rows,
        theory_metrics=theory_metrics,
        evaluation=theory_evaluation,
        meta=_build_meta(run_id_build),
        theory=_build_theory_descriptor(target_def, filters_payload),
        cohort=_build_cohort(len(micro_rows), target_def, odds_coverage_pct=odds_coverage_pct),
        modeling=modeling_status,
        monte_carlo=monte_carlo_status,
        notes=notes,
    )

