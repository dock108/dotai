"""Analyze endpoint and exports for EDA."""
from __future__ import annotations

import csv
import io
import math
import os
import pathlib
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
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import StreamingResponse
from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from .. import db_models
from ..db import AsyncSession, get_db
from ..services.derived_metrics import compute_derived_metrics
from ..services.feature_compute import compute_features_for_games
from ..services.feature_metadata import get_feature_metadata
from ..services.features.concept_detector import detect_concepts
from ..services.eda.micro_store import save_run, load_run, list_runs
from .sports_eda_helpers import (
    _resolve_layer_builder,
    _get_league,
    _resolve_target_definition,
    _target_value,
    _feature_policy_report,
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
    _pearson_correlation,
)
from .sports_eda_schemas import (
    AnalysisRequest,
    CorrelationResult,
    AnalysisResponse,
    AnalysisWithMicroResponse,
    CleaningSummary,
    MicroModelRow,
    ModelingStatus,
    MonteCarloStatus,
    AnalysisRunSummary,
    AnalysisRunDetail,
    GeneratedFeature,
)

MAX_GAMES_LIMIT = 5000
MC_MIN_ODDS_EVENTS = int(os.getenv("MC_MIN_ODDS_EVENTS", "1"))

router = APIRouter(prefix="/api/admin/sports/eda", tags=["sports-eda"])
logger = structlog.get_logger("sports-eda")


@router.get("/analysis-runs", response_model=list[AnalysisRunSummary])
async def list_analysis_runs() -> list[AnalysisRunSummary]:
    runs = list_runs()
    summaries: list[AnalysisRunSummary] = []
    for run_id, payload in runs.items():
        target = payload.get("target") if isinstance(payload, dict) else {}
        summaries.append(
            AnalysisRunSummary(
                run_id=run_id,
                created_at=payload.get("created_at") if isinstance(payload, dict) else None,
                target_name=(target or {}).get("target_name"),
                target_class=(target or {}).get("target_class"),
                run_type=payload.get("run_type") if isinstance(payload, dict) else None,
                micro_rows_ref=payload.get("micro_rows_ref") if isinstance(payload, dict) else None,
                cohort_size=payload.get("cohort_size") if isinstance(payload, dict) else None,
                snapshot_hash=payload.get("snapshot_hash") if isinstance(payload, dict) else None,
            )
        )
    summaries.sort(key=lambda r: r.created_at or "", reverse=True)
    return summaries


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunDetail)
async def get_analysis_run(run_id: str) -> AnalysisRunDetail:
    payload = load_run(run_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    micro_rows_sample = None
    micro_rows_ref = payload.get("micro_rows_ref") if isinstance(payload, dict) else None
    if micro_rows_ref and pathlib.Path(micro_rows_ref).exists():
        try:
            with pathlib.Path(micro_rows_ref).open() as f:
                reader = csv.DictReader(f)
                micro_rows_sample = []
                for idx, row in enumerate(reader):
                    if idx >= 200:
                        break
                    micro_rows_sample.append(row)
        except Exception:
            micro_rows_sample = None
    elif isinstance(payload, dict) and "micro_rows" in payload:
        try:
            mr = payload.get("micro_rows") or []
            micro_rows_sample = mr[:200]
        except Exception:
            micro_rows_sample = None

    return AnalysisRunDetail(
        run_id=run_id,
        created_at=payload.get("created_at") if isinstance(payload, dict) else None,
        request=payload.get("request") if isinstance(payload, dict) else None,
        target=payload.get("target") if isinstance(payload, dict) else None,
        evaluation=payload.get("evaluation") if isinstance(payload, dict) else None,
        modeling=payload.get("modeling") if isinstance(payload, dict) else None,
        monte_carlo=payload.get("monte_carlo") if isinstance(payload, dict) else None,
        mc_summary=payload.get("mc_summary") if isinstance(payload, dict) else None,
        model_snapshot=payload.get("model_snapshot") if isinstance(payload, dict) else None,
        micro_rows_ref=micro_rows_ref,
        micro_rows_sample=micro_rows_sample,
        run_type=payload.get("run_type") if isinstance(payload, dict) else None,
        cohort_size=payload.get("cohort_size") if isinstance(payload, dict) else None,
        snapshot_hash=payload.get("snapshot_hash") if isinstance(payload, dict) else None,
    )


@router.post("/analyze", response_model=AnalysisWithMicroResponse)
async def run_analysis(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> AnalysisWithMicroResponse:
    """Run feature correlation analysis and build micro rows."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    target_def = _resolve_target_definition(req.target_definition)
    requested_features = req.features or []
    filtered_features, policy = _feature_policy_report(requested_features, req.context)
    filtered_features = _drop_target_leakage(filtered_features, target_def)

    # Detect concepts to derive only the minimal required fields during Analyze.
    concept_info = detect_concepts(
        theory_text=getattr(target_def, "target_name", None),
        filters=req.model_dump(exclude={"features"}) if hasattr(req, "model_dump") else {},
    )
    concept_field_names = concept_info.get("auto_derived_fields", []) if concept_info else []
    concept_features: list[GeneratedFeature] = []
    for fname in concept_field_names:
        meta = get_feature_metadata(fname, "engineered")
        concept_features.append(
            GeneratedFeature(
                name=fname,
                formula=meta.formula if hasattr(meta, "formula") else fname,
                category="engineered",
                requires=[],
                timing=getattr(meta, "timing", None),
                source=getattr(meta, "source", None),
                group=getattr(meta, "group", None),
                default_selected=False,
            )
        )
    requested_for_compute = concept_features + filtered_features

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

    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    if req.games_limit:
        stmt = stmt.limit(min(req.games_limit, MAX_GAMES_LIMIT))
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]
    all_game_ids = await _filter_games_by_player(session, all_game_ids, getattr(req, "player", None))
    games = [g for g in games if g.id in all_game_ids]

    logger.info("analyze_games_filtered", game_count=len(all_game_ids), sample_ids=all_game_ids[:20])

    if not all_game_ids:
        return AnalysisResponse(
            sample_size=0,
            baseline_value=0.0,
            correlations=[],
            best_segments=[],
            insights=["No games found for the selected filters."],
            feature_policy=policy,
            detected_concepts=concept_info.get("detected_concepts") if concept_info else None,
            concept_derived_fields=concept_field_names or None,
        )

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, requested_for_compute, layer_builder=layer_builder, context=req.context
    )
    logger.info(
        "analyze_features_ready",
        game_count=len(all_game_ids),
        feature_count=len(requested_for_compute),
        explanatory_feature_count=len(filtered_features),
        concept_feature_count=len(concept_features),
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

    feature_names = [f.name for f in filtered_features]
    aligned_features, aligned_target, kept_ids, cleaning_summary = _prepare_dataset(
        feature_data, feature_names, game_to_targets, req.cleaning
    )

    sample_size = len(aligned_target)
    baseline_value = _safe_float(float(np.mean(aligned_target))) if aligned_target else 0.0
    if baseline_value is None:
        baseline_value = 0.0

    correlations: list[CorrelationResult] = []
    for fname in feature_names:
        corr = _pearson_correlation(aligned_features[fname], aligned_target)
        if corr is None:
            continue  # Skip features with invalid/NaN correlations
        significant = abs(corr) > 0.03 and sample_size >= 30
        correlations.append(CorrelationResult(feature=fname, correlation=corr, significant=significant))
    correlations.sort(key=lambda c: abs(c.correlation), reverse=True)

    insights_out = [f"Sample size: {sample_size} games"]
    if sample_size < 30:
        insights_out.append("⚠️ Sample size is very small; results may not be reliable.")

    micro_rows = _build_micro_rows(
        games,
        feature_data,
        kept_ids,
        game_to_targets,
        trigger_flag=True,
        target_def=target_def,
        model_prob_by_game_id=None,
        trigger_def=None,
    )
    theory_metrics = _compute_theory_metrics(micro_rows, target_def, None)
    theory_evaluation = _compute_theory_evaluation(micro_rows, target_def)
    odds_coverage_pct = float(sum(1 for r in micro_rows if r.closing_odds is not None) / len(micro_rows)) if micro_rows else 0.0

    mc_ok, mc_reason = _mc_eligibility(micro_rows, target_def)
    odds_present = any(r.closing_odds is not None for r in micro_rows)
    modeling_status = ModelingStatus(
        available=True,
        has_run=False,
        reason_not_run="user_has_not_requested",
        reason_not_available=None,
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
    run_id = str(uuid.uuid4())
    micro_rows_ref = _persist_micro_rows_csv(run_id, micro_rows)
    try:
        save_run(
            run_id,
            {
                "created_at": datetime.utcnow().isoformat(),
                "target": target_def.model_dump(),
                "request": req.model_dump() if hasattr(req, "model_dump") else req.dict(),
                "game_ids": all_game_ids,
                "micro_rows": [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in micro_rows],
                "evaluation": theory_evaluation.model_dump() if theory_evaluation and hasattr(theory_evaluation, "model_dump") else theory_evaluation,
                "modeling": modeling_status.model_dump() if hasattr(modeling_status, "model_dump") else None,
                "monte_carlo": monte_carlo_status.model_dump() if hasattr(monte_carlo_status, "model_dump") else None,
                "mc_summary": None,
                "micro_rows_ref": micro_rows_ref,
                "run_type": "analyze",
                "snapshot_hash": None,
                "cohort_size": sample_size,
            },
        )
    except Exception:
        pass

    logger.info("analyze_done", sample_size=sample_size, baseline_value=baseline_value, micro_rows=len(micro_rows))
    return AnalysisWithMicroResponse(
        sample_size=sample_size,
        baseline_value=baseline_value,
        correlations=correlations,
        best_segments=[],
        insights=insights_out,
        cleaning_summary=cleaning_summary,
        micro_rows=micro_rows,
        theory_metrics=theory_metrics,
        evaluation=theory_evaluation,
        feature_policy=policy,
        run_id=run_id,
        meta=_build_meta(run_id),
        theory=_build_theory_descriptor(target_def, filters_payload),
        cohort=_build_cohort(sample_size, target_def, odds_coverage_pct=odds_coverage_pct),
        modeling=modeling_status,
        monte_carlo=monte_carlo_status,
        notes=notes,
        detected_concepts=concept_info.get("detected_concepts") if concept_info else None,
        concept_derived_fields=concept_field_names or None,
    )


@router.post("/analyze/export")
async def export_analysis_csv(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Export the feature matrix with targets as CSV."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    filtered_features, _policy = _feature_policy_report(req.features or [], req.context)
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
    filtered_features, _policy = _feature_policy_report(req.features or [], req.context)
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
        writer.writerow(["game_id", "target_name", "market_type", "side", "closing_odds", "outcome", "pnl_units"])
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )

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
    _af, _at, kept_ids, _summary = _prepare_dataset(feature_data, feature_names, game_to_targets, req.cleaning)

    micro_rows = _build_micro_rows(
        games, feature_data, kept_ids, game_to_targets, trigger_flag=True, target_def=target_def
    )

    def csv_iter():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        header = [
            "game_id", "target_name", "market_type", "side", "closing_line", "closing_odds",
            "implied_prob", "model_prob", "edge_vs_implied", "outcome", "pnl_units", "est_ev_pct", "trigger_flag",
        ]
        writer.writerow(header)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for r in micro_rows:
            writer.writerow([
                r.game_id, r.target_name, r.market_type, r.side, r.closing_line, r.closing_odds,
                r.implied_prob, r.model_prob, r.edge_vs_implied, r.outcome, r.pnl_units, r.est_ev_pct, r.trigger_flag,
            ])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(csv_iter(), media_type="text/csv")

