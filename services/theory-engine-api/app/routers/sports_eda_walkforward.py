"""Walk-forward (blind replay) endpoint for EDA."""
from __future__ import annotations

import math
import os
import uuid
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
from fastapi import APIRouter, Depends
from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from .. import db_models
from ..db import AsyncSession, get_db
from ..services.derived_metrics import compute_derived_metrics
from ..services.feature_compute import compute_features_for_games
from ..services.model_builder import predict_proba, train_logistic_regression
from ..services.eda.micro_store import save_run
from ..utils.odds import implied_probability_from_american, profit_for_american_odds
from .sports_eda_helpers import (
    _resolve_layer_builder,
    _get_league,
    _resolve_target_definition,
    _target_value,
    _feature_policy_report,
    _prune_feature_matrix,
    _edge_half_life_days,
    _persist_predictions_csv,
)
from .sports_eda_shared import (
    _apply_base_filters,
    _filter_games_by_player,
    _prepare_dataset,
    _drop_target_leakage,
)
from .sports_eda_schemas import (
    WalkforwardRequest,
    WalkforwardResponse,
    WalkforwardSlice,
)

MAX_GAMES_LIMIT = 5000

router = APIRouter(prefix="/api/admin/sports/eda", tags=["sports-eda"])
logger = structlog.get_logger("sports-eda")


@router.post("/walkforward", response_model=WalkforwardResponse)
async def run_walkforward(req: WalkforwardRequest, session: AsyncSession = Depends(get_db)) -> WalkforwardResponse:
    """Rolling train/test evaluation for out-of-sample performance."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    target_def = _resolve_target_definition(req.target_definition)
    is_stat = target_def.target_class == "stat"
    filtered_features, _policy = _feature_policy_report(req.features, req.context)
    filtered_features = _drop_target_leakage(filtered_features, target_def)

    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    if req.games_limit:
        stmt = stmt.limit(min(req.games_limit, MAX_GAMES_LIMIT))
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]
    all_game_ids = await _filter_games_by_player(session, all_game_ids, getattr(req, "player", None))
    games = [g for g in games if g.id in all_game_ids]

    if not games:
        return WalkforwardResponse(run_id=str(uuid.uuid4()), slices=[], edge_half_life_days=None, notes=["No games found"])

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )

    game_to_target: dict[int, float] = {}
    date_map: dict[int, datetime] = {}
    odds_map: dict[int, float] = {}
    implied_map: dict[int, float] = {}
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
        if game.game_date:
            date_map[game.id] = game.game_date
        odds_val = None
        if target_def.market_type == "spread":
            odds_val = metrics.get("closing_spread_home_price") if target_def.side == "home" else metrics.get("closing_spread_away_price")
        elif target_def.market_type == "total":
            odds_val = metrics.get("closing_total_price")
        elif target_def.market_type == "moneyline":
            odds_val = metrics.get("closing_ml_home") if target_def.side == "home" else metrics.get("closing_ml_away")
        if odds_val is not None:
            odds_map[game.id] = float(odds_val)
            implied_map[game.id] = implied_probability_from_american(float(odds_val))

    feature_names = [f.name for f in filtered_features]

    # Determine date boundaries
    sorted_dates = sorted([d for d in date_map.values()])
    if not sorted_dates:
        return WalkforwardResponse(run_id=str(uuid.uuid4()), slices=[], edge_half_life_days=None, notes=["No dated games"])
    min_date = sorted_dates[0]
    max_date = sorted_dates[-1]

    window = req.window
    train_days = window.train_days or 180
    test_days = window.test_days or 14
    step_days = window.step_days or 7

    train_delta = timedelta(days=train_days)
    test_delta = timedelta(days=test_days)
    step_delta = timedelta(days=step_days)

    slices: list[WalkforwardSlice] = []
    predictions: list[dict[str, Any]] = []
    edges_for_half_life: list[tuple[datetime, float]] = []

    cursor = min_date + train_delta
    while cursor + test_delta <= max_date:
        train_start = cursor - train_delta
        train_end = cursor
        test_end = cursor + test_delta

        train_ids = [gid for gid, dt in date_map.items() if train_start <= dt < train_end and gid in game_to_target]
        test_ids = [gid for gid, dt in date_map.items() if train_end <= dt < test_end and gid in game_to_target]

        if not train_ids or not test_ids:
            cursor += step_delta
            continue

        train_data = [row for row in feature_data if row.get("game_id") in train_ids]
        test_data = [row for row in feature_data if row.get("game_id") in test_ids]

        train_target = {gid: game_to_target[gid] for gid in train_ids}
        test_target = {gid: game_to_target[gid] for gid in test_ids}

        aligned_features_train, aligned_target_train, kept_train, _ = _prepare_dataset(
            train_data, feature_names, train_target, req.cleaning
        )
        aligned_features_test, aligned_target_test, kept_test, _ = _prepare_dataset(
            test_data, feature_names, test_target, req.cleaning
        )

        if len(kept_train) < 30 or len(kept_test) < 5:
            cursor += step_delta
            continue

        pruned_features, _dropped_log = _prune_feature_matrix(aligned_features_train, feature_names)
        aligned_rows_train: list[dict[str, float]] = []
        for idx in range(len(aligned_target_train)):
            entry: dict[str, float] = {"__target__": aligned_target_train[idx]}
            for fname in pruned_features:
                val = aligned_features_train[fname][idx]
                entry[fname] = 0.0 if (val is None or np.isnan(val)) else float(val)
            aligned_rows_train.append(entry)

        trained = train_logistic_regression(aligned_rows_train, pruned_features, "__target__") if not is_stat else None

        slice_preds: list[dict[str, Any]] = []
        pnl_values: list[float] = []
        hits = 0
        obs = 0
        odds_present = 0
        edges_accum: list[float] = []
        for idx, gid in enumerate(kept_test):
            feature_row = {}
            for fname in pruned_features:
                val = aligned_features_test[fname][idx]
                feature_row[fname] = 0.0 if (val is None or np.isnan(val)) else float(val)
            model_prob = float(predict_proba(trained, {**feature_row, "__target__": 0.0})) if trained else None
            implied = implied_map.get(gid)
            outcome_val = aligned_target_test[idx] if idx < len(aligned_target_test) else None
            outcome = None
            pnl_units = None
            edge = None
            if target_def.target_class == "market":
                if outcome_val is not None:
                    obs += 1
                    if outcome_val == 1.0:
                        hits += 1
                if implied is not None:
                    odds_present += 1
                if model_prob is not None and implied is not None:
                    edge = float(model_prob - implied)
                    edges_accum.append(edge)
                if outcome_val is not None and implied is not None:
                    if outcome_val == 1.0:
                        pnl_units = profit_for_american_odds(float(odds_map.get(gid))) if odds_map.get(gid) is not None else 1.0
                    else:
                        pnl_units = -1.0
                    pnl_values.append(pnl_units)
                outcome = "win" if outcome_val == 1.0 else "loss" if outcome_val == 0.0 else None
            slice_preds.append(
                {
                    "game_id": gid,
                    "game_date": date_map.get(gid).isoformat() if date_map.get(gid) else None,
                    "model_prob": model_prob,
                    "implied_prob": implied,
                    "edge": edge,
                    "outcome": outcome,
                    "pnl_units": pnl_units,
                }
            )

        hit_rate = _safe_float(hits / obs) if obs else None
        roi_units = _safe_float(float(np.mean(pnl_values))) if pnl_values else None
        edge_avg = _safe_float(float(np.mean(edges_accum))) if edges_accum else None
        odds_cov = _safe_float(float(odds_present / len(kept_test))) if kept_test else 0.0
        slices.append(
            WalkforwardSlice(
                start_date=train_end,
                end_date=test_end,
                sample_size=len(kept_test),
                hit_rate=hit_rate,
                roi_units=roi_units,
                edge_avg=edge_avg,
                odds_coverage_pct=odds_cov,
            )
        )
        if edge_avg is not None and date_map.get(kept_test[0]):
            edges_for_half_life.append((date_map[kept_test[0]], edge_avg))
        predictions.extend(slice_preds)
        cursor += step_delta

    edge_half_life = _edge_half_life_days(edges_for_half_life)
    run_id = str(uuid.uuid4())
    predictions_ref = _persist_predictions_csv(run_id, predictions)
    try:
        save_run(
            run_id,
            {
                "created_at": datetime.utcnow().isoformat(),
                "target": target_def.model_dump(),
                "request": req.model_dump() if hasattr(req, "model_dump") else req.dict(),
                "slices": [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in slices],
                "edge_half_life_days": edge_half_life,
                "predictions_ref": predictions_ref,
                "run_type": "walkforward",
                "cohort_size": sum(s.sample_size for s in slices),
            },
        )
    except Exception:
        pass

    return WalkforwardResponse(
        run_id=run_id,
        slices=slices,
        edge_half_life_days=edge_half_life,
        predictions_ref=predictions_ref,
        notes=["Data-blind rolling evaluation"],
    )

