"""Micro row construction and evaluation utilities for EDA."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from .. import db_models
from ..services.derived_metrics import compute_derived_metrics
from ..utils.odds import implied_probability_from_american, profit_for_american_odds
from .sports_eda_schemas import (
    MicroModelRow,
    TargetDefinition,
    TriggerDefinition,
    TheoryMetrics,
    TheoryEvaluation,
)


def _safe_float(val: float | None) -> float | None:
    """Convert NaN/Inf to None for JSON compliance."""
    if val is None:
        return None
    if math.isnan(val) or math.isinf(val):
        return None
    return val


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

        winner = metrics.get("winner")
        total_result = metrics.get("total_result")

        if is_market:
            outcome = "win" if tgt == 1 else "loss" if tgt == 0 else "push"
            if outcome == "win" and odds_for_math is not None:
                pnl = profit_for_american_odds(float(odds_for_math), risk_units=1.0)
            elif outcome == "loss":
                pnl = -1.0
            else:
                pnl = 0.0
        else:
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

        reasons: list[str] = []
        did_trigger = bool(trigger_flag)
        if not is_market:
            did_trigger = False
            model_prob = None
            edge_vs_implied = None
            reasons.append("stat target: triggers disabled")
        else:
            if implied_prob is None:
                reasons.append("missing odds for implied probability")
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

        if did_trigger and model_prob is not None:
            reasons.insert(0, f"model_prob {model_prob:.3f} passes trigger")

        ev_pct = None
        
        # Extract game metadata for frontend display
        game_date_str = None
        home_team_name = None
        away_team_name = None
        home_score_val = None
        away_score_val = None
        
        if game:
            if game.game_date:
                game_date_str = game.game_date.strftime("%Y-%m-%d")
            # Try to get team names from relationship
            if hasattr(game, "home_team") and game.home_team:
                home_team_name = getattr(game.home_team, "name", None) or getattr(game.home_team, "abbreviation", None)
            if hasattr(game, "away_team") and game.away_team:
                away_team_name = getattr(game.away_team, "name", None) or getattr(game.away_team, "abbreviation", None)
            home_score_val = getattr(game, "home_score", None)
            away_score_val = getattr(game, "away_score", None)
        
        rows.append(
            MicroModelRow(
                theory_id=None,
                game_id=gid,
                # New game metadata fields
                game_date=game_date_str,
                home_team=home_team_name,
                away_team=away_team_name,
                home_score=home_score_val,
                away_score=away_score_val,
                # Target info
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
                final_score_home=home_score_val,  # Keep for backward compat
                final_score_away=away_score_val,  # Keep for backward compat
                outcome=outcome,
                pnl_units=pnl,
                est_ev_pct=ev_pct,
                trigger_flag=did_trigger,
                features={k: v for k, v in row.items() if k != "game_id"},
                meta={
                    "season": getattr(game, "season", None) if game else None,
                    "game_date": game_date_str,
                    "conference": getattr(game, "is_conference_game", None) if game else None,
                    "target_definition": td.model_dump() if hasattr(td, "model_dump") else td.dict() if td else None,
                    "trigger_definition": trig.model_dump() if hasattr(trig, "model_dump") else trig.dict(),
                    "trigger_reasons": reasons,
                    "odds_missing_reason": "missing closing odds" if (is_market and closing_odds is None) else None,
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
    cover_rate = _safe_float(sum(1 for r in eval_rows if r.outcome == "win") / n_eval) if n_eval else 0.0
    base_rate = None
    if baseline_rows:
        b_rows = [r for r in baseline_rows if r.outcome in {"win", "loss"}]
        b = len(b_rows)
        base_rate = _safe_float(sum(1 for r in b_rows if r.outcome == "win") / b) if b else None
    delta = _safe_float(cover_rate - base_rate) if base_rate is not None and cover_rate is not None else None
    implied = [r.implied_prob for r in eval_rows if r.implied_prob is not None]
    ev_vs_implied = _safe_float((cover_rate - float(np.mean(implied))) * 100.0) if implied and cover_rate is not None else None
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
    max_dd = _safe_float(max_dd)
    sharpe_like = None
    pnl_changes = [r.pnl_units for r in eval_rows if r.pnl_units is not None]
    if len(pnl_changes) > 1:
        sharpe_like = _safe_float(float(np.mean(pnl_changes) / (np.std(pnl_changes) + 1e-9)))
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
    """Evaluation vs baseline (stat or market) independent of modeling."""
    if not rows:
        return None

    if target_def.target_class == "stat":
        values: list[float] = []
        stability: dict[str, list[float]] = {}
        stability_month: dict[str, list[float]] = {}
        for r in rows:
            if isinstance(r.target_value, (int, float)):
                values.append(float(r.target_value))
                season = (r.meta or {}).get("season")
                if season is not None:
                    stability.setdefault(str(season), []).append(float(r.target_value))
                game_date = (r.meta or {}).get("game_date")
                if isinstance(game_date, str) and len(game_date) >= 7:
                    stability_month.setdefault(game_date[:7], []).append(float(r.target_value))
        if not values:
            return None
        cohort = _safe_float(float(np.mean(values)))
        baseline = cohort
        delta = _safe_float(cohort - baseline) if baseline is not None and cohort is not None else None
        stability_mean = {k: _safe_float(float(np.mean(v))) for k, v in stability.items() if v}
        stability_mean = {k: v for k, v in stability_mean.items() if v is not None}
        stability_month_mean = {k: _safe_float(float(np.mean(v))) for k, v in stability_month.items() if v}
        stability_month_mean = {k: v for k, v in stability_month_mean.items() if v is not None}
        cohort_std = _safe_float(float(np.std(values))) if len(values) > 1 else None
        cohort_min = _safe_float(float(np.min(values))) if values else None
        cohort_max = _safe_float(float(np.max(values))) if values else None
        q25 = _safe_float(float(np.quantile(values, 0.25))) if values else None
        q75 = _safe_float(float(np.quantile(values, 0.75))) if values else None
        verdict = "noise" if delta is None or abs(delta) < 0.5 else ("interesting" if abs(delta) > 2 else "weak")
        return TheoryEvaluation(
            target_class="stat",
            sample_size=len(values),
            cohort_value=cohort,
            baseline_value=baseline,
            delta_value=delta,
            cohort_std=cohort_std,
            cohort_min=cohort_min,
            cohort_max=cohort_max,
            p25=q25,
            p75=q75,
            formatting="numeric",
            notes=["Observational theory — no betting simulation."],
            stability_by_season=stability_mean or None,
            stability_by_month=stability_month_mean or None,
            verdict=verdict,
        )

    # Market target
    eval_rows = [r for r in rows if r.outcome in {"win", "loss"}]
    n_eval = len(eval_rows)
    if n_eval == 0:
        return None
    hits = sum(1 for r in eval_rows if r.outcome == "win")
    cohort = _safe_float(hits / n_eval)
    implied_list = [r.implied_prob for r in eval_rows if r.implied_prob is not None]
    baseline = _safe_float(float(np.mean(implied_list))) if implied_list else 0.5
    delta = _safe_float(cohort - baseline) if cohort is not None and baseline is not None else None
    roi_units = _safe_float(float(np.mean([r.pnl_units or 0.0 for r in eval_rows]))) if eval_rows else None
    verdict = "noise" if delta is None or abs(delta) < 0.02 else ("interesting" if abs(delta) > 0.05 else "weak")
    stability: dict[str, list[float]] = {}
    for r in eval_rows:
        season = (r.meta or {}).get("season")
        if season is not None:
            stability.setdefault(str(season), []).append(1.0 if r.outcome == "win" else 0.0)
    stability_mean = {k: _safe_float(float(np.mean(v))) for k, v in stability.items() if v}
    stability_mean = {k: v for k, v in stability_mean.items() if v is not None}
    stability_month: dict[str, list[float]] = {}
    for r in eval_rows:
        game_date = (r.meta or {}).get("game_date")
        if isinstance(game_date, str) and len(game_date) >= 7:
            stability_month.setdefault(game_date[:7], []).append(1.0 if r.outcome == "win" else 0.0)
    stability_month_mean = {k: _safe_float(float(np.mean(v))) for k, v in stability_month.items() if v}
    stability_month_mean = {k: v for k, v in stability_month_mean.items() if v is not None}
    return TheoryEvaluation(
        target_class="market",
        sample_size=n_eval,
        cohort_value=cohort,
        baseline_value=baseline,
        delta_value=delta,
        implied_rate=baseline,
        roi_units=roi_units,
        formatting="percent",
        notes=None,
        stability_by_season=stability_mean or None,
        stability_by_month=stability_month_mean or None,
        verdict=verdict,
    )

