from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

try:
    from pydantic import BaseModel, field_validator
except ImportError:  # pragma: no cover
    from pydantic import BaseModel, validator as field_validator


class FeatureGenerationRequest(BaseModel):
    league_code: str
    raw_stats: list[str]
    include_rest_days: bool = False
    include_rolling: bool = False
    rolling_window: int = 5


class GeneratedFeature(BaseModel):
    name: str
    formula: str
    category: str
    requires: list[str]
    timing: str | None = None
    source: str | None = None
    group: str | None = None


class FeatureGenerationResponse(BaseModel):
    features: list[GeneratedFeature]
    summary: str


class CleaningOptions(BaseModel):
    drop_if_all_null: bool = False
    drop_if_any_null: bool = False
    drop_if_non_numeric: bool = False
    min_non_null_features: int | None = None


class CleaningSummary(BaseModel):
    raw_rows: int
    rows_after_cleaning: int
    dropped_null: int
    dropped_non_numeric: int


class FeatureQualityStats(BaseModel):
    nulls: int
    null_pct: float
    non_numeric: int
    distinct_count: int
    count: int
    min: float | None
    max: float | None
    mean: float | None


class FeaturePreviewSummary(BaseModel):
    rows_inspected: int
    feature_stats: dict[str, FeatureQualityStats]


class FeaturePreviewRequest(BaseModel):
    league_code: str
    features: list[GeneratedFeature]
    seasons: list[int] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    phase: Optional[Literal["all", "out_conf", "conf", "postseason"]] = None
    recent_days: Optional[int] = None
    home_spread_min: float | None = None
    home_spread_max: float | None = None
    team: str | None = None
    player: str | None = None
    limit: int | None = None
    offset: int | None = None
    target: str | None = None
    include_target: bool = False
    format: str = "csv"
    sort_by: str | None = None
    sort_dir: str | None = None
    feature_filter: list[str] | None = None
    feature_mode: str | None = None
    context: Literal["deployable", "diagnostic"] = "deployable"
    target_definition: Optional["TargetDefinition"] = None

    @field_validator("home_spread_max")
    @classmethod
    def _validate_spread(cls, v, info):
        min_v = info.data.get("home_spread_min")
        if v is not None and min_v is not None and v < min_v:
            raise ValueError("home_spread_max must be >= home_spread_min")
        return v


class TargetDefinition(BaseModel):
    target_class: Literal["stat", "market"]
    target_name: str
    metric_type: Literal["numeric", "binary"]
    market_type: Literal["spread", "total", "moneyline"] | None = None
    side: Literal["home", "away", "over", "under"] | None = None
    odds_required: bool = True

    @field_validator("market_type")
    @classmethod
    def _validate_market_type(cls, v, info):
        if info.data.get("target_class") == "market" and v is None:
            raise ValueError("market_type is required for market targets")
        return v

    @field_validator("side")
    @classmethod
    def _validate_side(cls, v, info):
        if info.data.get("target_class") != "market":
            return None
        mt = (info.data.get("market_type") or "").lower()
        if mt in {"spread", "moneyline"} and v not in {"home", "away"}:
            raise ValueError("side must be 'home' or 'away' for spread/moneyline markets")
        if mt == "total" and v not in {"over", "under"}:
            raise ValueError("side must be 'over' or 'under' for total markets")
        return v


class AnalysisRequest(BaseModel):
    league_code: str
    features: list[GeneratedFeature]
    seasons: list[int] | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    phase: Optional[Literal["all", "out_conf", "conf", "postseason"]] = None
    recent_days: Optional[int] = None
    home_spread_min: float | None = None
    home_spread_max: float | None = None
    went_over_total: bool | None = None
    pace_min: float | None = None
    pace_max: float | None = None
    team: str | None = None
    player: str | None = None
    minutes_trigger: Literal["actual_lt_rolling"] | None = None
    games_limit: int | None = None
    cleaning: CleaningOptions | None = None
    feature_mode: str | None = None
    context: Literal["deployable", "diagnostic"] = "deployable"
    target_definition: TargetDefinition
    trigger_definition: Optional["TriggerDefinition"] = None
    exposure_controls: Optional["ExposureControls"] = None

    @field_validator("home_spread_max")
    @classmethod
    def _validate_spread(cls, v, info):
        min_v = info.data.get("home_spread_min")
        if v is not None and min_v is not None and v < min_v:
            raise ValueError("home_spread_max must be >= home_spread_min")
        return v

    @field_validator("pace_max")
    @classmethod
    def _validate_pace(cls, v, info):
        min_v = info.data.get("pace_min")
        if v is not None and min_v is not None and v < min_v:
            raise ValueError("pace_max must be >= pace_min")
        return v


class CorrelationResult(BaseModel):
    feature: str
    correlation: float
    p_value: float | None = None
    is_significant: bool = False


class SegmentResult(BaseModel):
    condition: str
    sample_size: int
    hit_rate: float
    baseline_rate: float
    edge: float


class CleaningSummaryResponse(BaseModel):
    cleaning_summary: CleaningSummary | None = None


class AnalysisResponse(BaseModel):
    sample_size: int
    baseline_rate: float
    correlations: list[CorrelationResult]
    best_segments: list[SegmentResult]
    insights: list[str]
    cleaning_summary: CleaningSummary | None = None
    feature_policy: dict[str, Any] | None = None
    run_id: str | None = None


class ModelBuildRequest(BaseModel):
    league_code: str
    features: list[GeneratedFeature]
    seasons: list[int] | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    phase: Optional[Literal["all", "out_conf", "conf", "postseason"]] = None
    recent_days: Optional[int] = None
    home_spread_min: float | None = None
    home_spread_max: float | None = None
    went_over_total: bool | None = None
    pace_min: float | None = None
    pace_max: float | None = None
    team: str | None = None
    player: str | None = None
    minutes_trigger: Literal["actual_lt_rolling"] | None = None
    games_limit: int | None = None
    cleaning: CleaningOptions | None = None
    feature_mode: str | None = None
    context: Literal["deployable", "diagnostic"] = "deployable"
    target_definition: TargetDefinition
    trigger_definition: Optional["TriggerDefinition"] = None
    exposure_controls: Optional["ExposureControls"] = None

    @field_validator("home_spread_max")
    @classmethod
    def _validate_spread(cls, v, info):
        min_v = info.data.get("home_spread_min")
        if v is not None and min_v is not None and v < min_v:
            raise ValueError("home_spread_max must be >= home_spread_min")
        return v

    @field_validator("pace_max")
    @classmethod
    def _validate_pace(cls, v, info):
        min_v = info.data.get("pace_min")
        if v is not None and min_v is not None and v < min_v:
            raise ValueError("pace_max must be >= pace_min")
        return v


class MicroModelRow(BaseModel):
    theory_id: str | None = None
    game_id: int
    target_name: str
    target_value: float | str | None = None
    baseline_value: float | None = None
    market_type: str | None = None
    side: str | None = None
    closing_line: float | None = None
    closing_odds: float | None = None
    implied_prob: float | None = None
    final_score_home: int | None = None
    final_score_away: int | None = None
    outcome: str | None = None
    pnl_units: float | None = None
    est_ev_pct: float | None = None
    model_prob: float | None = None
    edge_vs_implied: float | None = None
    trigger_flag: bool = True
    features: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class TheoryMetrics(BaseModel):
    sample_size: int
    cover_rate: float
    baseline_cover_rate: float | None = None
    delta_cover: float | None = None
    ev_vs_implied: float | None = None
    sharpe_like: float | None = None
    max_drawdown: float | None = None
    time_stability: float | None = None


class TrainedModelResponse(BaseModel):
    model_type: str
    features_used: list[str]
    feature_weights: dict[str, float]
    accuracy: float
    roi: float
    bias: float | None = None


class SuggestedTheoryResponse(BaseModel):
    text: str
    features_used: list[str]
    historical_edge: float
    confidence: str


class ModelBuildResponse(BaseModel):
    model_summary: TrainedModelResponse
    suggested_theories: list[SuggestedTheoryResponse]
    validation_stats: dict[str, float]
    cleaning_summary: CleaningSummary | None = None
    run_id: str | None = None
    feature_policy: dict[str, Any] | None = None
    features_dropped: list[dict[str, Any]] | None = None
    exposure_summary: dict[str, Any] | None = None
    bet_tape: list[dict[str, Any]] | None = None
    performance_slices: dict[str, Any] | None = None
    failure_analysis: dict[str, Any] | None = None
    mc_assumptions: dict[str, Any] | None = None
    mc_interpretation: list[str] | None = None
    theory_candidates: list[dict[str, Any]] | None = None
    model_snapshot: dict[str, Any] | None = None


class AnalysisWithMicroResponse(AnalysisResponse):
    micro_model_results: list[MicroModelRow] | None = None
    theory_metrics: TheoryMetrics | None = None


class ModelBuildWithMicroResponse(ModelBuildResponse):
    micro_model_results: list[MicroModelRow] | None = None
    theory_metrics: TheoryMetrics | None = None
    mc_summary: dict[str, Any] | None = None


class TriggerDefinition(BaseModel):
    prob_threshold: float = 0.55
    confidence_band: float | None = None
    min_edge_vs_implied: float | None = None

    @field_validator("prob_threshold")
    @classmethod
    def _validate_prob_threshold(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("prob_threshold must be between 0 and 1")
        return v

    @field_validator("confidence_band")
    @classmethod
    def _validate_conf_band(cls, v):
        if v is None:
            return v
        if not (0.0 <= v <= 0.5):
            raise ValueError("confidence_band must be between 0 and 0.5")
        return v

    @field_validator("min_edge_vs_implied")
    @classmethod
    def _validate_edge(cls, v):
        if v is None:
            return v
        if not (-1.0 <= v <= 1.0):
            raise ValueError("min_edge_vs_implied must be between -1 and 1")
        return v


class ExposureControls(BaseModel):
    max_bets_per_day: int | None = 5
    max_bets_per_side_per_day: int | None = None
    spread_abs_min: float | None = None
    spread_abs_max: float | None = None

    @field_validator("max_bets_per_day")
    @classmethod
    def _validate_max_bets(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("max_bets_per_day must be >= 0")
        return v

    @field_validator("max_bets_per_side_per_day")
    @classmethod
    def _validate_max_side(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("max_bets_per_side_per_day must be >= 0")
        return v

    @field_validator("spread_abs_max")
    @classmethod
    def _validate_spread_abs(cls, v, info):
        mn = info.data.get("spread_abs_min")
        if v is not None and mn is not None and v < mn:
            raise ValueError("spread_abs_max must be >= spread_abs_min")
        return v


