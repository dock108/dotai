"""Theory Builder endpoints using the new TheoryDraft schema.

This router accepts the new canonical TheoryDraft shape and internally
converts to the existing analysis pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from ..db import AsyncSession, get_db
from .theory_draft_schema import TheoryDraft, TheoryAnalysisResponse
from .theory_draft_translator import is_legacy_payload, translate_legacy_theory
from ..services.features.context_presets import get_preset_features, expand_context_features
from .sports_eda_schemas import (
    AnalysisRequest,
    TargetDefinition,
    GeneratedFeature,
    TriggerDefinition,
    ExposureControls,
    CleaningOptions,
)
from .sports_eda_analyze import run_analysis as legacy_run_analysis

router = APIRouter(prefix="/api/admin/theory", tags=["theory-builder"])
logger = structlog.get_logger("theory-builder")


def _theory_draft_to_analysis_request(draft: TheoryDraft) -> AnalysisRequest:
    """Convert TheoryDraft to legacy AnalysisRequest for reuse of existing pipeline."""

    # Convert time window to seasons/dates
    seasons = None
    recent_days = None
    date_start = None
    date_end = None

    tw = draft.time_window
    if tw.mode == "current_season":
        # Use current year as season
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
    )

    # Convert to legacy request and run existing pipeline
    legacy_req = _theory_draft_to_analysis_request(draft)
    legacy_response = await legacy_run_analysis(legacy_req, session)

    # Convert response to new shape
    evaluation = legacy_response.evaluation.model_dump() if legacy_response.evaluation else None
    micro_rows = [r.model_dump() for r in legacy_response.micro_rows] if legacy_response.micro_rows else None

    return TheoryAnalysisResponse(
        run_id=legacy_response.run_id or str(uuid.uuid4()),
        sample_size=legacy_response.sample_size,
        baseline_value=legacy_response.baseline_value,
        cohort_value=evaluation.get("cohort_value") if evaluation else None,
        delta_value=evaluation.get("delta_value") if evaluation else None,
        detected_concepts=legacy_response.detected_concepts or [],
        concept_fields=legacy_response.concept_derived_fields or [],
        correlations=[c.model_dump() for c in legacy_response.correlations],
        evaluation=evaluation,
        micro_rows=micro_rows,
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

