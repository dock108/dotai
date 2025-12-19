"""Theory Builder endpoints using the new TheoryDraft schema.

This router accepts the new canonical TheoryDraft shape and internally
converts to the existing analysis pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import numpy as np
import structlog
from fastapi import APIRouter, Depends, HTTPException

from ..db import AsyncSession, get_db
from .theory_draft_schema import (
    TheoryDraft,
    TheoryAnalysisResponse,
    CohortDefinition,
    SampleGame,
    CohortRule,
)
from .theory_draft_translator import is_legacy_payload, translate_legacy_theory
from ..services.features.context_presets import get_preset_features, expand_context_features
from .sports_eda_schemas import (
    AnalysisRequest,
    TargetDefinition,
    GeneratedFeature,
    TriggerDefinition,
    ExposureControls,
)
from .sports_eda_analyze import run_analysis as legacy_run_analysis

router = APIRouter(prefix="/api/admin/theory", tags=["theory-builder"])
logger = structlog.get_logger("theory-builder")


def _safe_float(val: Any) -> float | None:
    """Convert value to float, returning None for NaN/Inf."""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _build_cohort_rule_description(cohort_rule: CohortRule) -> str:
    """Build human-readable description of the cohort rule."""
    if cohort_rule.mode == "auto":
        return "Auto-discovered (best split using selected stats)"
    
    if cohort_rule.mode == "quantile" and cohort_rule.quantile_rules:
        parts = [
            f"{qr.stat} in {qr.direction} {qr.percentile}%"
            for qr in cohort_rule.quantile_rules
        ]
        return " AND ".join(parts)
    
    if cohort_rule.mode == "threshold" and cohort_rule.threshold_rules:
        parts = [
            f"{tr.stat} {tr.operator} {tr.value}"
            for tr in cohort_rule.threshold_rules
        ]
        return " AND ".join(parts)
    
    return "No rule defined"


def _theory_draft_to_analysis_request(draft: TheoryDraft) -> AnalysisRequest:
    """Convert TheoryDraft to legacy AnalysisRequest for reuse of existing pipeline."""

    # Convert time window to seasons/dates
    seasons = None
    recent_days = None
    date_start = None
    date_end = None

    tw = draft.time_window
    if tw.mode == "current_season":
        current_year = datetime.utcnow().year
        seasons = [current_year]
    elif tw.mode == "last_30":
        recent_days = 30
    elif tw.mode == "last_60":
        recent_days = 60
    elif tw.mode == "last_n" and isinstance(tw.value, int):
        recent_days = tw.value
    elif tw.mode == "specific_seasons" and isinstance(tw.value, list):
        seasons = tw.value
    elif tw.mode == "custom":
        date_start = tw.start_date
        date_end = tw.end_date

    # Convert target to TargetDefinition
    target_type = draft.target.type
    if target_type == "game_total":
        target_def = TargetDefinition(
            target_class="stat",
            target_name=draft.target.stat or "combined_score",
            metric_type=draft.target.metric,
            odds_required=False,
        )
    elif target_type == "spread_result":
        target_def = TargetDefinition(
            target_class="market",
            target_name="did_home_cover",
            metric_type="binary",
            market_type="spread",
            side=draft.target.side or "home",
            odds_required=True,
        )
    elif target_type == "moneyline_win":
        target_def = TargetDefinition(
            target_class="market",
            target_name="winner",
            metric_type="binary",
            market_type="moneyline",
            side=draft.target.side or "home",
            odds_required=True,
        )
    elif target_type == "team_stat":
        target_def = TargetDefinition(
            target_class="stat",
            target_name=draft.target.stat or "turnovers",
            metric_type=draft.target.metric,
            odds_required=False,
        )
    else:
        target_def = TargetDefinition(
            target_class="stat",
            target_name="combined_score",
            metric_type="numeric",
            odds_required=False,
        )

    # Build features from base_stats + context
    features: list[GeneratedFeature] = []

    # Generate raw/diff/combined features from base stats
    for stat in draft.inputs.base_stats:
        # Raw home/away
        features.append(GeneratedFeature(
            name=f"home_{stat}",
            formula=f"home {stat}",
            category="raw",
            requires=[stat],
        ))
        features.append(GeneratedFeature(
            name=f"away_{stat}",
            formula=f"away {stat}",
            category="raw",
            requires=[stat],
        ))
        # Differential
        features.append(GeneratedFeature(
            name=f"{stat}_diff",
            formula=f"home_{stat} - away_{stat}",
            category="differential",
            requires=[stat],
        ))
        # Combined (for scoring stats)
        if stat in ("pts", "points", "fg", "fg3", "ft", "orb", "drb", "reb", "ast", "stl", "blk", "tov", "pf"):
            features.append(GeneratedFeature(
                name=f"total_{stat}",
                formula=f"home_{stat} + away_{stat}",
                category="combined",
                requires=[stat],
            ))

    # Add context features based on preset or custom selection
    # IMPORTANT: "minimal" preset should add NOTHING - only base stats derived features
    if draft.context.preset != "minimal":
        context_features = draft.context.features
        if draft.context.preset != "custom":
            preset_features = get_preset_features(draft.context.preset)
            context_features = draft.context.features.model_copy(update=preset_features)

        # Map context feature names to GeneratedFeature objects
        context_feature_names = expand_context_features(context_features.model_dump())
        for fname in context_feature_names:
            features.append(GeneratedFeature(
                name=fname,
                formula=fname,
                category="engineered",
                requires=[],
            ))

    # Context mode
    context = "diagnostic" if draft.diagnostics.allow_post_game_features else "deployable"

    return AnalysisRequest(
        league_code=draft.league,
        features=features if features else None,
        seasons=seasons,
        date_start=date_start,
        date_end=date_end,
        phase=draft.filters.phase,
        recent_days=recent_days,
        home_spread_min=draft.filters.spread_abs_min,
        home_spread_max=draft.filters.spread_abs_max,
        team=draft.filters.team,
        player=draft.filters.player,
        context=context,
        target_definition=target_def,
        trigger_definition=TriggerDefinition(
            prob_threshold=draft.model.prob_threshold,
            confidence_band=draft.model.confidence_band,
            min_edge_vs_implied=draft.model.min_edge_vs_implied,
        ) if draft.model.enabled else None,
        exposure_controls=ExposureControls(
            max_bets_per_day=draft.exposure.max_bets_per_day,
            max_bets_per_side_per_day=draft.exposure.max_per_side_per_day,
            spread_abs_min=draft.exposure.spread_abs_min,
            spread_abs_max=draft.exposure.spread_abs_max,
        ),
    )


def _extract_sample_games(
    micro_rows: list[dict[str, Any]] | None,
    target_type: str,
    limit: int = 25,
) -> list[SampleGame]:
    """Extract sample games with full data from micro rows."""
    if not micro_rows:
        return []
    
    games = []
    for row in micro_rows[:limit]:
        # Try to extract game data from various possible field names
        game_id = str(row.get("game_id", row.get("id", "")))
        
        # Date - try multiple formats
        game_date = row.get("game_date", row.get("date", ""))
        if isinstance(game_date, datetime):
            game_date = game_date.strftime("%Y-%m-%d")
        else:
            game_date = str(game_date)[:10] if game_date else ""
        
        # Teams
        home_team = str(row.get("home_team", row.get("home", "")))
        away_team = str(row.get("away_team", row.get("away", "")))
        
        # Scores
        home_score = int(row.get("home_score", row.get("home_pts", 0)) or 0)
        away_score = int(row.get("away_score", row.get("away_pts", 0)) or 0)
        
        # Target value based on target type
        if target_type == "spread_result":
            target_value = row.get("spread", row.get("closing_spread_home", 0))
        elif target_type == "game_total":
            target_value = row.get("total", row.get("closing_total", home_score + away_score))
        elif target_type == "moneyline_win":
            target_value = row.get("ml_home", row.get("closing_ml_home", ""))
        else:
            target_value = row.get("target", row.get("target_value", 0))
        
        # Outcome - try to determine from available fields
        outcome_raw = row.get("outcome", row.get("result", row.get("hit", None)))
        if outcome_raw is not None:
            if isinstance(outcome_raw, bool):
                outcome = "W" if outcome_raw else "L"
            elif isinstance(outcome_raw, (int, float)):
                outcome = "W" if outcome_raw > 0 else "L"
            else:
                outcome = str(outcome_raw)[:10]
        else:
            # Try to compute from target
            if target_type == "spread_result":
                did_cover = row.get("did_cover", row.get("did_home_cover"))
                if did_cover is not None:
                    outcome = "Cover" if did_cover else "Miss"
                else:
                    outcome = "—"
            elif target_type == "game_total":
                over = row.get("went_over", row.get("total_result"))
                if over is not None:
                    outcome = "O" if over else "U"
                else:
                    outcome = "—"
            elif target_type == "moneyline_win":
                winner = row.get("winner", row.get("home_win"))
                if winner is not None:
                    outcome = "W" if winner else "L"
                else:
                    outcome = "—"
            else:
                outcome = "—"
        
        games.append(SampleGame(
            game_id=game_id,
            game_date=game_date,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            target_value=target_value if target_value is not None else 0,
            outcome=outcome,
        ))
    
    return games


@router.post("/analyze", response_model=TheoryAnalysisResponse)
async def analyze_theory(
    draft: TheoryDraft,
    session: AsyncSession = Depends(get_db),
) -> TheoryAnalysisResponse:
    """Analyze a theory using the new TheoryDraft schema."""
    logger.info(
        "theory_analyze_start",
        league=draft.league,
        target_type=draft.target.type,
        base_stats=draft.inputs.base_stats,
        context_preset=draft.context.preset,
        cohort_rule_mode=draft.cohort_rule.mode,
    )

    # Convert to legacy request and run existing pipeline
    legacy_req = _theory_draft_to_analysis_request(draft)
    legacy_response = await legacy_run_analysis(legacy_req, session)

    # Extract evaluation data
    evaluation = legacy_response.evaluation.model_dump() if legacy_response.evaluation else {}
    micro_rows = [r.model_dump() for r in legacy_response.micro_rows] if legacy_response.micro_rows else []
    
    # Compute cohort metrics - single source of truth
    baseline_value = _safe_float(legacy_response.baseline_value) or 0.5
    cohort_value = _safe_float(evaluation.get("cohort_value", evaluation.get("cohort_mean"))) or baseline_value
    
    # CRITICAL: delta MUST equal cohort - baseline
    delta_value = cohort_value - baseline_value
    
    sample_size = legacy_response.sample_size
    
    # Build cohort definition
    cohort_definition = CohortDefinition(
        rule_description=_build_cohort_rule_description(draft.cohort_rule),
        discovered_split=draft.cohort_rule.discovered_rule,
        sample_size=sample_size,
        feature_set_used=draft.context.preset,
    )
    
    # Extract sample games with full data
    sample_games = _extract_sample_games(micro_rows, draft.target.type)
    
    # Determine if we should show detected concepts
    # Only show if: rule mode is "auto" OR context is not "minimal"
    should_show_concepts = (
        draft.cohort_rule.mode == "auto" or 
        draft.context.preset != "minimal"
    )
    
    detected_concepts = (
        legacy_response.detected_concepts or []
    ) if should_show_concepts else []
    
    concept_fields = (
        legacy_response.concept_derived_fields or []
    ) if should_show_concepts else []

    # Build correlations - ensure proper format
    correlations = []
    for c in legacy_response.correlations:
        corr_dict = c.model_dump() if hasattr(c, "model_dump") else dict(c)
        correlations.append({
            "feature": corr_dict.get("feature", ""),
            "correlation": _safe_float(corr_dict.get("correlation", 0)) or 0,
        })

    return TheoryAnalysisResponse(
        run_id=legacy_response.run_id or str(uuid.uuid4()),
        cohort_definition=cohort_definition,
        sample_size=sample_size,
        baseline_value=baseline_value,
        cohort_value=cohort_value,
        delta_value=delta_value,
        detected_concepts=detected_concepts,
        concept_fields=concept_fields,
        correlations=correlations,
        sample_games=sample_games,
        evaluation=evaluation if evaluation else None,
        micro_rows=micro_rows if micro_rows else None,
        modeling_available=legacy_response.modeling.available if legacy_response.modeling else True,
        mc_available=legacy_response.monte_carlo.available if legacy_response.monte_carlo else False,
        mc_reason=legacy_response.monte_carlo.reason_not_available if legacy_response.monte_carlo else None,
        notes=legacy_response.notes or [],
    )


@router.post("/analyze-any")
async def analyze_any_payload(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_db),
) -> TheoryAnalysisResponse:
    """Accept either new TheoryDraft or legacy payload.

    This endpoint handles the transition period.
    """
    if is_legacy_payload(payload):
        logger.warning("legacy_payload_received", keys=list(payload.keys()))
        draft = translate_legacy_theory(payload)
    else:
        draft = TheoryDraft.model_validate(payload)

    return await analyze_theory(draft, session)
