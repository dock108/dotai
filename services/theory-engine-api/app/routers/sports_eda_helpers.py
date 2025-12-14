"""Shared helper functions for EDA routers."""
from __future__ import annotations

from datetime import datetime
import csv
import json
import os
import hashlib
import pathlib
from typing import Any

import structlog
from sqlalchemy import select
from fastapi import HTTPException, status

from .. import db_models
from ..db import AsyncSession
from ..services.eda.targeting import resolve_target_definition, target_value
from ..services.eda.feature_policy import feature_policy_report
from ..services.eda.pruning import prune_feature_matrix
from ..services.eda.exposure import apply_exposure_controls, build_bet_tape
from ..services.eda.slicing import build_performance_slices, build_failure_analysis
from ..services.eda.mc_text import mc_assumptions_payload, mc_interpretation_lines
from ..services.eda.theory_candidates import generate_theory_candidates
from .sports_eda_schemas import (
    GeneratedFeature,
    ModelBuildRequest,
    MicroModelRow,
    MetaInfo,
    TheoryDescriptor,
    CohortInfo,
    TargetDefinition,
    TriggerDefinition,
    ExposureControls,
)
from engine.common.feature_layers import build_combined_feature_builder  # type: ignore

logger = structlog.get_logger("sports-eda")
MC_MIN_ODDS_EVENTS = int(os.getenv("MC_MIN_ODDS_EVENTS", "1"))


def _resolve_layer_builder(mode: str | None):
    if not mode:
        return None
    normalized = mode.lower()
    if normalized not in {"admin", "full"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="feature_mode must be 'admin' or 'full'")
    return build_combined_feature_builder(normalized)


async def _get_league(session: AsyncSession, code: str) -> db_models.SportsLeague:
    stmt = select(db_models.SportsLeague).where(db_models.SportsLeague.code == code.upper())
    result = await session.execute(stmt)
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"League {code} not found")
    return league


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
    baseline_value: float,
    target_def: TargetDefinition,
    min_sample_size: int = 150,
    min_lift: float = 0.02,
) -> list[dict[str, Any]]:
    td_dict = target_def.model_dump() if hasattr(target_def, "model_dump") else target_def
    return generate_theory_candidates(
        aligned_rows,
        feature_names,
        baseline_rate=baseline_value,
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


def _build_cohort(sample_size: int, target_def: TargetDefinition, odds_coverage_pct: float | None = None) -> CohortInfo:
    baseline_type = "stat_mean" if target_def.target_class == "stat" else "implied_prob"
    baseline_desc = "Mean of target values" if target_def.target_class == "stat" else "Average implied probability from odds"
    return CohortInfo(
        sample_size=sample_size,
        time_span=None,
        baseline_definition={"type": baseline_type, "description": baseline_desc},
        odds_coverage_pct=odds_coverage_pct,
    )


def _mc_eligibility(rows: list[MicroModelRow], target_def: TargetDefinition) -> tuple[bool, str | None]:
    if target_def.target_class != "market":
        return False, "stat_target_no_mc"
    odds_count = sum(1 for r in rows if r.closing_odds is not None)
    if odds_count >= MC_MIN_ODDS_EVENTS:
        return True, None
    return False, "missing_odds"


def _edge_half_life_days(edges: list[tuple[datetime, float]]) -> float | None:
    if not edges:
        return None
    edges_sorted = sorted(edges, key=lambda x: x[0])
    init_edge = edges_sorted[0][1]
    if init_edge is None or init_edge == 0:
        return None
    target = init_edge / 2.0
    for dt, e in edges_sorted[1:]:
        if e is None:
            continue
        if e <= target:
            delta_days = (dt - edges_sorted[0][0]).days
            return float(delta_days)
    return None


def _persist_micro_rows_csv(run_id: str, micro_rows: list[MicroModelRow]) -> str | None:
    if not micro_rows:
        return None
    out_dir = pathlib.Path(os.environ.get("EDA_RUNS_DIR", "/tmp/eda_runs"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}.csv"
    fieldnames = [
        "theory_id",
        "game_id",
        "target_name",
        "market_type",
        "side",
        "closing_line",
        "closing_odds",
        "implied_prob",
        "model_prob",
        "edge_vs_implied",
        "outcome",
        "pnl_units",
        "est_ev_pct",
        "trigger_flag",
    ]
    feature_keys: set[str] = set()
    for r in micro_rows:
        if r.features:
            feature_keys.update(r.features.keys())
    fieldnames.extend(sorted(feature_keys))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in micro_rows:
            base = {
                "theory_id": r.theory_id,
                "game_id": r.game_id,
                "target_name": r.target_name,
                "market_type": r.market_type,
                "side": r.side,
                "closing_line": r.closing_line,
                "closing_odds": r.closing_odds,
                "implied_prob": r.implied_prob,
                "model_prob": r.model_prob,
                "edge_vs_implied": r.edge_vs_implied,
                "outcome": r.outcome,
                "pnl_units": r.pnl_units,
                "est_ev_pct": r.est_ev_pct,
                "trigger_flag": r.trigger_flag,
            }
            if r.features:
                base.update({k: v for k, v in r.features.items() if k in feature_keys})
            writer.writerow(base)
    return str(path)


def _persist_predictions_csv(run_id: str, rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    out_dir = pathlib.Path(os.environ.get("EDA_RUNS_DIR", "/tmp/eda_runs"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}-walkforward.csv"
    keys: set[str] = set()
    for r in rows:
        keys.update(r.keys())
    fieldnames = sorted(keys)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return str(path)
