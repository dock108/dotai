"""New canonical TheoryDraft schema.

This is the production shape for all theory definitions.
UI emits this shape, backend persists this shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

try:
    from pydantic import BaseModel, field_validator
except ImportError:  # pragma: no cover
    from pydantic import BaseModel, validator as field_validator


# -----------------------------------------------------------------------------
# Time Window
# -----------------------------------------------------------------------------


class TimeWindow(BaseModel):
    """Time window specification."""

    mode: Literal["current_season", "last_30", "last_60", "last_n", "custom", "specific_seasons"]
    value: int | list[int] | None = None  # days for last_n, season list for specific_seasons
    start_date: datetime | None = None  # for custom
    end_date: datetime | None = None  # for custom


# -----------------------------------------------------------------------------
# Target
# -----------------------------------------------------------------------------


class Target(BaseModel):
    """What we're trying to explain/predict."""

    type: Literal["game_total", "spread_result", "moneyline_win", "team_stat"]
    stat: str | None = None  # e.g. "combined_score", "turnovers"
    metric: Literal["numeric", "binary"] = "numeric"
    side: Literal["home", "away", "over", "under"] | None = None


# -----------------------------------------------------------------------------
# Inputs
# -----------------------------------------------------------------------------


class Inputs(BaseModel):
    """Base stats used as modeling inputs."""

    base_stats: list[str] = []
    feature_policy: Literal["auto", "manual"] = "auto"


# -----------------------------------------------------------------------------
# Context Features (by semantic group)
# -----------------------------------------------------------------------------


class ContextFeatures(BaseModel):
    """Semantic groupings of context features."""

    game: list[str] = []  # conference_game, rest_days, pace
    market: list[str] = []  # closing_spread, closing_total, implied_prob
    team: list[str] = []  # rating_diff, projections
    player: list[str] = []  # player_minutes, player_minutes_rolling
    diagnostic: list[str] = []  # cover_margin, total_delta (post-game leaky)


class Context(BaseModel):
    """Context configuration."""

    preset: Literal["minimal", "standard", "market_aware", "player_aware", "custom"] = "minimal"
    features: ContextFeatures = ContextFeatures()


# -----------------------------------------------------------------------------
# Filters (optional overrides)
# -----------------------------------------------------------------------------


class Filters(BaseModel):
    """Optional filters to narrow the data slice."""

    team: str | None = None
    player: str | None = None
    phase: Literal["all", "out_conf", "conf", "postseason"] | None = None
    market_type: Literal["spread", "total", "moneyline"] | None = None
    season_type: str | None = None
    spread_abs_min: float | None = None
    spread_abs_max: float | None = None


# -----------------------------------------------------------------------------
# Model Configuration
# -----------------------------------------------------------------------------


class ModelConfig(BaseModel):
    """Model-related settings."""

    enabled: bool = False
    prob_threshold: float = 0.55
    confidence_band: float | None = None
    min_edge_vs_implied: float | None = None


# -----------------------------------------------------------------------------
# Exposure Controls
# -----------------------------------------------------------------------------


class ExposureConfig(BaseModel):
    """Exposure/position sizing controls."""

    max_bets_per_day: int | None = 5
    max_per_side_per_day: int | None = None
    spread_abs_min: float | None = None
    spread_abs_max: float | None = None
    ranking: Literal["edge", "prob", "ev"] = "edge"


# -----------------------------------------------------------------------------
# Results Configuration
# -----------------------------------------------------------------------------


class ResultsConfig(BaseModel):
    """What to show/export in results."""

    columns: list[str] = []
    include_team_stats: list[str] = []
    include_player_stats: list[str] = []


# -----------------------------------------------------------------------------
# Diagnostics
# -----------------------------------------------------------------------------


class DiagnosticsConfig(BaseModel):
    """Diagnostic mode settings."""

    allow_post_game_features: bool = False


# -----------------------------------------------------------------------------
# Cohort Rule - REQUIRED: defines what games are "in the cohort"
# -----------------------------------------------------------------------------


class QuantileRule(BaseModel):
    """A quantile-based cohort rule."""
    stat: str  # e.g. "turnovers_diff"
    direction: Literal["top", "bottom"]  # top 20% or bottom 20%
    percentile: int  # 10, 20, 25, etc.


class ThresholdRule(BaseModel):
    """A threshold-based cohort rule."""
    stat: str  # e.g. "turnovers_diff"
    operator: Literal[">=", "<=", ">", "<", "="]
    value: float


class CohortRule(BaseModel):
    """Cohort rule defining what games are included."""
    mode: Literal["auto", "quantile", "threshold"] = "auto"
    quantile_rules: list[QuantileRule] = []
    threshold_rules: list[ThresholdRule] = []
    discovered_rule: str | None = None  # Backend populates for auto mode


# -----------------------------------------------------------------------------
# Main TheoryDraft
# -----------------------------------------------------------------------------


class TheoryDraft(BaseModel):
    """The canonical theory definition shape.

    This is the single source of truth for theory configuration.
    """

    theory_id: str = "auto"
    league: str
    time_window: TimeWindow
    target: Target
    inputs: Inputs = Inputs()
    cohort_rule: CohortRule = CohortRule()  # REQUIRED: how we decide what games are in cohort
    context: Context = Context()
    filters: Filters = Filters()
    model: ModelConfig = ModelConfig()
    exposure: ExposureConfig = ExposureConfig()
    results: ResultsConfig = ResultsConfig()
    diagnostics: DiagnosticsConfig = DiagnosticsConfig()


# -----------------------------------------------------------------------------
# Response Types
# -----------------------------------------------------------------------------


class CohortDefinition(BaseModel):
    """Description of what games are included in the cohort."""
    rule_description: str  # Human-readable: "turnovers_diff in top 20%"
    discovered_split: str | None = None  # If auto mode, what was found
    sample_size: int
    feature_set_used: str  # "minimal", "standard", etc.


class SampleGame(BaseModel):
    """A single game in the sample with full data."""
    game_id: str
    game_date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    target_value: float | str  # Spread, total, or win indicator
    outcome: str  # "W", "L", "O", "U", "Cover", "Miss"


class TheoryAnalysisResponse(BaseModel):
    """Response from theory analysis.
    
    IMPORTANT: delta_value MUST equal cohort_value - baseline_value.
    The UI relies on this for correct rendering.
    """

    run_id: str
    # REQUIRED: Cohort definition - must be shown first in results
    cohort_definition: CohortDefinition
    # Core metrics (single source of truth - no recomputation in UI)
    sample_size: int
    baseline_value: float
    cohort_value: float
    delta_value: float  # MUST equal cohort_value - baseline_value
    # Concepts - only populated if rule mode is auto OR context is not minimal
    detected_concepts: list[str] = []
    concept_fields: list[str] = []
    # Correlations - only from eligible features
    correlations: list[dict[str, Any]] = []
    # Sample games with full data
    sample_games: list[SampleGame] = []
    # Optional extended data
    evaluation: dict[str, Any] | None = None
    micro_rows: list[dict[str, Any]] | None = None
    modeling_available: bool = True
    mc_available: bool = False
    mc_reason: str | None = None
    notes: list[str] = []

