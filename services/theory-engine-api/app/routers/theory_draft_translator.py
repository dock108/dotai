"""Translator from legacy payload to TheoryDraft.

This exists ONLY to keep things working during the cutover.
Remove this as soon as the UI is switched to the new shape.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import structlog

from .theory_draft_schema import (
    TheoryDraft,
    TimeWindow,
    Target,
    Inputs,
    Context,
    ContextFeatures,
    Filters,
    ModelConfig,
    ExposureConfig,
    ResultsConfig,
    DiagnosticsConfig,
)

logger = structlog.get_logger("theory-draft-translator")

# Counter for legacy usage - remove when translator is removed
_legacy_usage_count = 0


def _increment_legacy_counter() -> int:
    """Track legacy payload usage. Remove with translator."""
    global _legacy_usage_count
    _legacy_usage_count += 1
    return _legacy_usage_count


def get_legacy_usage_count() -> int:
    """Get current legacy usage count."""
    return _legacy_usage_count


def is_legacy_payload(payload: dict[str, Any]) -> bool:
    """Check if payload is in legacy format.

    Legacy payloads have:
    - league_code (not league)
    - target_definition (not target)
    - features array (not inputs.base_stats)
    """
    if "league_code" in payload and "league" not in payload:
        return True
    if "target_definition" in payload and "target" not in payload:
        return True
    if "features" in payload and "inputs" not in payload:
        return True
    return False


def translate_legacy_theory(payload: dict[str, Any]) -> TheoryDraft:
    """Translate legacy AnalysisRequest/ModelBuildRequest to TheoryDraft.

    This is an input adapter only. Remove when cutover is complete.
    """
    count = _increment_legacy_counter()
    logger.warning(
        "legacy_payload_translated",
        count=count,
        has_features=bool(payload.get("features")),
        has_target_definition=bool(payload.get("target_definition")),
    )

    # Extract league
    league = payload.get("league_code") or payload.get("league", "NBA")

    # Translate time window
    time_window = _translate_time_window(payload)

    # Translate target
    target = _translate_target(payload.get("target_definition", {}))

    # Translate inputs (base stats from features)
    inputs = _translate_inputs(payload.get("features", []))

    # Translate context (from features)
    context = _translate_context(payload.get("features", []), payload.get("context"))

    # Translate filters
    filters = _translate_filters(payload)

    # Translate model config
    model_config = _translate_model_config(payload.get("trigger_definition"))

    # Translate exposure
    exposure = _translate_exposure(payload.get("exposure_controls"))

    # Diagnostics
    diagnostics = DiagnosticsConfig(
        allow_post_game_features=payload.get("context") == "diagnostic"
    )

    return TheoryDraft(
        theory_id="auto",
        league=league,
        time_window=time_window,
        target=target,
        inputs=inputs,
        context=context,
        filters=filters,
        model=model_config,
        exposure=exposure,
        results=ResultsConfig(),
        diagnostics=diagnostics,
    )


def _translate_time_window(payload: dict[str, Any]) -> TimeWindow:
    """Translate legacy season/date fields to TimeWindow."""
    seasons = payload.get("seasons")
    recent_days = payload.get("recent_days")
    date_start = payload.get("date_start")
    date_end = payload.get("date_end")

    if recent_days:
        if recent_days <= 30:
            return TimeWindow(mode="last_30")
        elif recent_days <= 60:
            return TimeWindow(mode="last_60")
        else:
            return TimeWindow(mode="last_n", value=recent_days)

    if date_start or date_end:
        return TimeWindow(
            mode="custom",
            start_date=date_start,
            end_date=date_end,
        )

    if seasons:
        return TimeWindow(mode="specific_seasons", value=seasons)

    return TimeWindow(mode="current_season")


def _translate_target(target_def: dict[str, Any]) -> Target:
    """Translate legacy TargetDefinition to Target."""
    target_class = target_def.get("target_class", "stat")
    target_name = target_def.get("target_name", "combined_score")
    metric_type = target_def.get("metric_type", "numeric")
    market_type = target_def.get("market_type")
    side = target_def.get("side")

    # Map to new target types
    if target_class == "stat":
        if target_name in ("combined_score", "final_total_points"):
            return Target(type="game_total", stat=target_name, metric=metric_type)
        else:
            return Target(type="team_stat", stat=target_name, metric=metric_type)
    else:  # market
        if market_type == "spread":
            return Target(type="spread_result", metric="binary", side=side)
        elif market_type == "moneyline":
            return Target(type="moneyline_win", metric="binary", side=side)
        elif market_type == "total":
            return Target(type="game_total", metric="binary", side=side)
        else:
            return Target(type="game_total", stat="combined_score", metric="numeric")


def _translate_inputs(features: list[dict[str, Any]]) -> Inputs:
    """Extract base stats from legacy features list."""
    base_stats: set[str] = set()

    for f in features:
        category = f.get("category", "")
        requires = f.get("requires", [])

        # Raw/differential/combined features have requires that are the base stats
        if category in ("raw", "differential", "combined") and requires:
            base_stats.update(requires)

    return Inputs(base_stats=list(base_stats), feature_policy="auto")


def _translate_context(features: list[dict[str, Any]], context_mode: str | None) -> Context:
    """Translate legacy features to context configuration."""
    game_features: list[str] = []
    market_features: list[str] = []
    team_features: list[str] = []
    player_features: list[str] = []
    diagnostic_features: list[str] = []

    # Known feature mappings
    game_context = {"is_conference_game", "pace_game", "pace_home_possessions",
                    "pace_away_possessions", "home_rest_days", "away_rest_days", "rest_advantage"}
    market_context = {"closing_spread_home", "closing_total", "ml_implied_edge"}
    team_context = {"rating_diff", "proj_points_diff"}
    player_context = {"player_minutes", "player_minutes_rolling", "player_minutes_delta"}
    diagnostic_context = {"final_total_points", "total_delta", "cover_margin"}

    for f in features:
        name = f.get("name", "")
        if name in game_context:
            game_features.append(name)
        elif name in market_context:
            market_features.append(name)
        elif name in team_context:
            team_features.append(name)
        elif name in player_context:
            player_features.append(name)
        elif name in diagnostic_context:
            diagnostic_features.append(name)

    # Determine preset based on what's included
    preset = "custom"
    if not any([game_features, market_features, team_features, player_features]):
        preset = "minimal"
    elif player_features:
        preset = "player_aware"
    elif market_features:
        preset = "market_aware"
    elif game_features or team_features:
        preset = "standard"

    return Context(
        preset=preset,
        features=ContextFeatures(
            game=game_features,
            market=market_features,
            team=team_features,
            player=player_features,
            diagnostic=diagnostic_features if context_mode == "diagnostic" else [],
        ),
    )


def _translate_filters(payload: dict[str, Any]) -> Filters:
    """Translate legacy filter fields."""
    return Filters(
        team=payload.get("team"),
        player=payload.get("player"),
        phase=payload.get("phase"),
        market_type=None,  # not in legacy
        season_type=None,  # not in legacy
        spread_abs_min=payload.get("home_spread_min"),
        spread_abs_max=payload.get("home_spread_max"),
    )


def _translate_model_config(trigger_def: dict[str, Any] | None) -> ModelConfig:
    """Translate legacy TriggerDefinition to ModelConfig."""
    if not trigger_def:
        return ModelConfig()

    return ModelConfig(
        enabled=False,  # model not enabled by default
        prob_threshold=trigger_def.get("prob_threshold", 0.55),
        confidence_band=trigger_def.get("confidence_band"),
        min_edge_vs_implied=trigger_def.get("min_edge_vs_implied"),
    )


def _translate_exposure(exposure_controls: dict[str, Any] | None) -> ExposureConfig:
    """Translate legacy ExposureControls to ExposureConfig."""
    if not exposure_controls:
        return ExposureConfig()

    return ExposureConfig(
        max_bets_per_day=exposure_controls.get("max_bets_per_day", 5),
        max_per_side_per_day=exposure_controls.get("max_bets_per_side_per_day"),
        spread_abs_min=exposure_controls.get("spread_abs_min"),
        spread_abs_max=exposure_controls.get("spread_abs_max"),
    )

