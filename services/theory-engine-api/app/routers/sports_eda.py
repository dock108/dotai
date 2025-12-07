"""Admin EDA endpoints for sports data.

These endpoints power internal exploratory analysis and will eventually
serve as the backbone modeling interface for matchup evaluation and
simulations. They are **admin-only** and are not exposed to end users.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import csv
import io
from typing import Any, Literal, Optional
import statistics

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import StreamingResponse
try:
    # Pydantic v2
    from pydantic import BaseModel, field_validator
except ImportError:  # pragma: no cover
    # Fallback for pydantic v1
    from pydantic import BaseModel, validator as field_validator
from sqlalchemy import Select, func, select, text, and_, or_
from sqlalchemy.orm import selectinload, aliased

from .. import db_models
from ..db import AsyncSession, get_db
import numpy as np

from engine.common.feature_layers import build_combined_feature_builder

from ..services.derived_metrics import compute_derived_metrics
from ..services.feature_compute import compute_features_for_games
from ..services.feature_engine import GeneratedFeature as GeneratedFeatureDTO, generate_features, summarize_features
from ..services.model_builder import TrainedModel, train_logistic_regression
from ..services.theory_generator import SuggestedTheory, generate_theories
from ..services.historical_mc import simulate_historical_mc
from ..utils.odds import implied_probability_from_decimal
from ..db_models import SportsPlayerBoxscore

MAX_GAMES_LIMIT = 5000

router = APIRouter(prefix="/api/admin/sports/eda", tags=["sports-eda"])


# ---------- Feature generation ----------


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
    start_date: datetime | None = None  # deprecated, use date_start/date_end
    end_date: datetime | None = None    # deprecated, use date_start/date_end
    date_start: datetime | None = None
    date_end: datetime | None = None
    phase: Optional[Literal["all", "out_conf", "conf", "postseason"]] = None  # NCAAB-only
    recent_days: Optional[int] = None  # rolling window constraint
    home_spread_min: float | None = None
    home_spread_max: float | None = None
    team: str | None = None
    player: str | None = None
    limit: int | None = None
    offset: int | None = None
    target: str | None = None  # optional target for CSV export
    include_target: bool = False
    format: str = "csv"  # "csv" | "json"
    sort_by: str | None = None  # "null_pct" | "non_numeric" | "name"
    sort_dir: str | None = None  # "asc" | "desc"
    feature_filter: list[str] | None = None
    feature_mode: str | None = None  # "admin" | "full"

    @field_validator("home_spread_max")
    @classmethod
    def _validate_spread(cls, v, info):
        min_v = info.data.get("home_spread_min")
        if v is not None and min_v is not None and v < min_v:
            raise ValueError("home_spread_max must be >= home_spread_min")
        return v


class AnalysisRequest(BaseModel):
    league_code: str
    features: list[GeneratedFeature]
    target: Literal["cover", "win", "over"]
    seasons: list[int] | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    phase: Optional[Literal["all", "out_conf", "conf", "postseason"]] = None  # NCAAB-only
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
    feature_mode: str | None = None  # "admin" | "full"

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


class AnalysisResponse(BaseModel):
    sample_size: int
    baseline_rate: float
    correlations: list[CorrelationResult]
    best_segments: list[SegmentResult]
    insights: list[str]
    cleaning_summary: CleaningSummary | None = None


class ModelBuildRequest(BaseModel):
    league_code: str
    features: list[GeneratedFeature]
    target: Literal["cover", "win", "over"]
    seasons: list[int] | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    phase: Optional[Literal["all", "out_conf", "conf", "postseason"]] = None  # NCAAB-only
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
    feature_mode: str | None = None  # "admin" | "full"

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
    market_type: str
    side: str
    closing_line: float | None = None
    closing_odds: float | None = None
    implied_prob: float | None = None
    final_score_home: int | None = None
    final_score_away: int | None = None
    outcome: str | None = None  # win/loss/push
    pnl_units: float | None = None
    est_ev_pct: float | None = None
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


class AnalysisWithMicroResponse(AnalysisResponse):
    micro_model_results: list[MicroModelRow] | None = None
    theory_metrics: TheoryMetrics | None = None


class ModelBuildWithMicroResponse(ModelBuildResponse):
    micro_model_results: list[MicroModelRow] | None = None
    theory_metrics: TheoryMetrics | None = None
    mc_summary: dict[str, Any] | None = None


async def _get_league(session: AsyncSession, code: str) -> db_models.SportsLeague:
    stmt = select(db_models.SportsLeague).where(db_models.SportsLeague.code == code.upper())
    result = await session.execute(stmt)
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"League {code} not found")
    return league


def _resolve_layer_builder(mode: str | None):
    if not mode:
        return None
    normalized = mode.lower()
    if normalized not in {"admin", "full"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="feature_mode must be 'admin' or 'full'")
    return build_combined_feature_builder(normalized)


def _apply_base_filters(stmt: Select, league: db_models.SportsLeague, req: Any) -> Select:
    """Apply shared filters (season, date, conference, spreads, team)."""
    stmt = stmt.where(db_models.SportsGame.league_id == league.id)
    seasons = getattr(req, "seasons", None)
    if seasons:
        stmt = stmt.where(db_models.SportsGame.season.in_(seasons))
    date_start = getattr(req, "date_start", None) or getattr(req, "start_date", None)
    date_end = getattr(req, "date_end", None) or getattr(req, "end_date", None)
    if date_start:
        stmt = stmt.where(db_models.SportsGame.game_date >= date_start)
    if date_end:
        stmt = stmt.where(db_models.SportsGame.game_date <= date_end)
    # Phase filter (NCAAB only): out_conf (< Jan 1), conf (Jan 1–Mar 15), postseason (Mar 16+)
    phase = getattr(req, "phase", None)
    phase_ranges = _build_phase_ranges(getattr(league, "code", None), seasons, phase)
    if phase_ranges:
        clauses = [
            and_(db_models.SportsGame.game_date >= start_dt, db_models.SportsGame.game_date < end_dt)
            for start_dt, end_dt in phase_ranges
        ]
        stmt = stmt.where(or_(*clauses))
    # Recent rolling window (from today backwards)
    recent_days = getattr(req, "recent_days", None)
    if recent_days:
        cutoff = datetime.utcnow() - timedelta(days=recent_days)
        stmt = stmt.where(db_models.SportsGame.game_date >= cutoff)
    # Spread filters (home)
    spread_min = getattr(req, "home_spread_min", None)
    spread_max = getattr(req, "home_spread_max", None)
    if spread_min is not None or spread_max is not None:
        stmt = stmt.join(db_models.SportsGameOdds, db_models.SportsGameOdds.game_id == db_models.SportsGame.id)
        stmt = stmt.where(db_models.SportsGameOdds.market_type == "spread", db_models.SportsGameOdds.side == "home")
        if spread_min is not None:
            stmt = stmt.where(db_models.SportsGameOdds.line >= spread_min)
        if spread_max is not None:
            stmt = stmt.where(db_models.SportsGameOdds.line <= spread_max)
    # Team filter
    team = getattr(req, "team", None)
    if team:
        team_filter = f"%{team.lower()}%"
        away_team = aliased(db_models.SportsTeam)
        stmt = stmt.join(db_models.SportsTeam, db_models.SportsGame.home_team_id == db_models.SportsTeam.id, isouter=True)
        stmt = stmt.join(away_team, db_models.SportsGame.away_team_id == away_team.id, isouter=True)
        stmt = stmt.where(
            func.lower(db_models.SportsTeam.name).like(team_filter)
            | func.lower(db_models.SportsTeam.short_name).like(team_filter)
            | func.lower(db_models.SportsTeam.abbreviation).like(team_filter)
            | func.lower(away_team.name).like(team_filter)
            | func.lower(away_team.short_name).like(team_filter)
            | func.lower(away_team.abbreviation).like(team_filter)
        )
    return stmt


def _build_phase_ranges(league_code: str | None, seasons: list[int] | None, phase: str | None):
    """
    Build date ranges for NCAAB phases:
    - out_conf: season start (Jul 1 prior year) to Jan 1 of next calendar year
    - conf: Jan 1 to Mar 16
    - postseason: Mar 16 to Jul 1
    """
    if not league_code or league_code.upper() != "NCAAB":
        return None
    if not seasons or not phase or phase == "all":
        return None
    ranges: list[tuple[datetime, datetime]] = []
    for s in seasons:
        # Season s spans roughly Jul (prior) through July (next)
        season_start = datetime(s, 7, 1)
        conf_year = s + 1  # Jan/Mar fall in next calendar year
        out_end = datetime(conf_year, 1, 1)
        conf_start = out_end
        conf_end = datetime(conf_year, 3, 16)
        post_start = conf_end
        post_end = datetime(conf_year, 7, 1)
        if phase == "out_conf":
            ranges.append((season_start, out_end))
        elif phase == "conf":
            ranges.append((conf_start, conf_end))
        elif phase == "postseason":
            ranges.append((post_start, post_end))
    return ranges if ranges else None


async def _filter_games_by_player(session: AsyncSession, game_ids: list[int], player: str | None) -> list[int]:
    if not player or not game_ids:
        return game_ids
    stmt = (
        select(SportsPlayerBoxscore.game_id)
        .where(SportsPlayerBoxscore.game_id.in_(game_ids))
        .where(func.lower(SportsPlayerBoxscore.player_name).like(f"%{player.lower()}%"))
    )
    res = await session.execute(stmt)
    return [gid for gid, in res.fetchall()]


class AvailableStatKeysResponse(BaseModel):
    """Response with available stat keys for a league."""

    league_code: str
    team_stat_keys: list[str]
    player_stat_keys: list[str]


@router.get("/stat-keys/{league_code}", response_model=AvailableStatKeysResponse)
async def get_available_stat_keys(
    league_code: str,
    session: AsyncSession = Depends(get_db),
) -> AvailableStatKeysResponse:
    """Get available team and player stat keys for a given league.

    Extracts distinct keys from the JSONB stats columns in the database
    for use in the EDA UI multi-select dropdowns.
    """
    league = await _get_league(session, league_code)

    # Get distinct team stat keys using jsonb_object_keys
    team_keys_query = text("""
        SELECT DISTINCT key
        FROM sports_team_boxscores tb
        JOIN sports_games g ON tb.game_id = g.id
        CROSS JOIN LATERAL jsonb_object_keys(tb.stats) AS key
        WHERE g.league_id = :league_id
        ORDER BY key
    """)
    team_result = await session.execute(team_keys_query, {"league_id": league.id})
    team_stat_keys = [row[0] for row in team_result.fetchall()]

    # Get distinct player stat keys using jsonb_object_keys
    player_keys_query = text("""
        SELECT DISTINCT key
        FROM sports_player_boxscores pb
        JOIN sports_games g ON pb.game_id = g.id
        CROSS JOIN LATERAL jsonb_object_keys(pb.stats) AS key
        WHERE g.league_id = :league_id
        ORDER BY key
    """)
    player_result = await session.execute(player_keys_query, {"league_id": league.id})
    player_stat_keys = [row[0] for row in player_result.fetchall()]

    return AvailableStatKeysResponse(
        league_code=league.code,
        team_stat_keys=team_stat_keys,
        player_stat_keys=player_stat_keys,
    )


@router.post("/generate-features", response_model=FeatureGenerationResponse)
async def generate_feature_catalog(req: FeatureGenerationRequest) -> FeatureGenerationResponse:
    """Generate feature descriptors based on selected raw stats and context flags."""
    generated = generate_features(
        raw_stats=req.raw_stats,
        include_rest_days=req.include_rest_days,
        include_rolling=req.include_rolling,
        rolling_window=req.rolling_window,
    )
    features = [
        GeneratedFeature(
            name=f.name,
            formula=f.formula,
            category=f.category,
            requires=f.requires,
        )
        for f in generated
    ]
    return FeatureGenerationResponse(
        features=features,
        summary=summarize_features(generated, req.raw_stats, req.include_rest_days),
    )


def _target_value(metrics: dict[str, Any], target: str) -> float | None:
    if target == "cover":
        val = metrics.get("did_home_cover")
        return 1.0 if val else 0.0 if val is not None else None
    if target == "win":
        val = metrics.get("winner")
        return 1.0 if val == "home" else 0.0 if val == "away" else None
    if target == "over":
        val = metrics.get("total_result")
        return 1.0 if val == "over" else 0.0 if val == "under" else None
    return None


def _pearson_correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) < 5:
        return None
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    if np.std(x_arr) == 0 or np.std(y_arr) == 0:
        return None
    return float(np.corrcoef(x_arr, y_arr)[0, 1])


def _coerce_numeric(val: Any) -> tuple[float | None, bool]:
    """Return (numeric_value, is_non_numeric)."""
    if val is None:
        return None, False
    if isinstance(val, (int, float)):
        return float(val), False
    if isinstance(val, str):
        if val.strip() == "":
            return None, False
        try:
            return float(val), False
        except ValueError:
            return None, True
    return None, True


def _prepare_dataset(
    feature_data: list[dict[str, Any]],
    feature_names: list[str],
    target_map: dict[int, float],
    cleaning: CleaningOptions | None,
) -> tuple[dict[str, list[float]], list[float], list[int], CleaningSummary]:
    aligned_features: dict[str, list[float]] = {name: [] for name in feature_names}
    aligned_target: list[float] = []
    kept_ids: list[int] = []
    raw_rows = 0
    dropped_null = 0
    dropped_non_numeric = 0

    for row in feature_data:
        gid = row.get("game_id")
        if gid not in target_map:
            continue
        raw_rows += 1

        coerced_values: list[float | None] = []
        non_null_count = 0
        any_null = False
        has_non_numeric = False

        for name in feature_names:
            num_val, is_non_numeric = _coerce_numeric(row.get(name))
            if is_non_numeric:
                has_non_numeric = True
            if num_val is not None:
                non_null_count += 1
            else:
                any_null = True
            coerced_values.append(num_val)

        all_null = non_null_count == 0
        drop_row = False
        if cleaning:
            if cleaning.drop_if_non_numeric and has_non_numeric:
                drop_row = True
                dropped_non_numeric += 1
            elif cleaning.drop_if_any_null and any_null:
                drop_row = True
                dropped_null += 1
            elif cleaning.drop_if_all_null and all_null:
                drop_row = True
                dropped_null += 1
            elif cleaning.min_non_null_features is not None and non_null_count < cleaning.min_non_null_features:
                drop_row = True
                dropped_null += 1

        if drop_row:
            continue

        kept_ids.append(gid)
        aligned_target.append(target_map[gid])
        for name, val in zip(feature_names, coerced_values):
            aligned_features[name].append(np.nan if val is None else val)

    summary = CleaningSummary(
        raw_rows=raw_rows,
        rows_after_cleaning=len(aligned_target),
        dropped_null=dropped_null,
        dropped_non_numeric=dropped_non_numeric,
    )
    return aligned_features, aligned_target, kept_ids, summary


def _compute_quality_stats(
    feature_data: list[dict[str, Any]], feature_names: list[str]
) -> dict[str, FeatureQualityStats]:
    rows = len(feature_data)
    stats: dict[str, FeatureQualityStats] = {}
    for name in feature_names:
        nulls = 0
        non_numeric = 0
        numeric_values: list[float] = []
        distinct_values: set[Any] = set()
        for row in feature_data:
            num_val, is_non_numeric = _coerce_numeric(row.get(name))
            if num_val is None and not is_non_numeric:
                nulls += 1
            if is_non_numeric:
                non_numeric += 1
            if num_val is not None:
                numeric_values.append(num_val)
            val = row.get(name)
            if val is not None:
                distinct_values.add(val)

        count = len(numeric_values)
        min_val = min(numeric_values) if numeric_values else None
        max_val = max(numeric_values) if numeric_values else None
        mean_val = float(np.mean(numeric_values)) if numeric_values else None
        null_pct = float(nulls / rows) if rows else 0.0
        stats[name] = FeatureQualityStats(
            nulls=nulls,
            null_pct=null_pct,
            non_numeric=non_numeric,
            distinct_count=len(distinct_values),
            count=count,
            min=min_val,
            max=max_val,
            mean=mean_val,
        )
    return stats


def _build_micro_rows(
    games: list[db_models.SportsGame],
    feature_data: list[dict[str, Any]],
    kept_ids: list[int],
    target_map: dict[int, float],
    trigger_flag: bool = True,
) -> list[MicroModelRow]:
    """Construct micro_model_results rows aligned to kept_ids."""
    game_lookup = {g.id: g for g in games}
    rows: list[MicroModelRow] = []
    for row in feature_data:
        gid = row.get("game_id")
        if gid not in kept_ids:
            continue
        game = game_lookup.get(gid)
        metrics = compute_derived_metrics(game, game.odds or []) if game else {}
        closing_line = metrics.get("closing_spread_home")
        closing_odds = metrics.get("closing_spread_home_price")
        implied_prob = implied_probability_from_decimal(row.get("market_decimal_odds")) if row.get("market_decimal_odds") else None
        tgt = target_map.get(gid)
        outcome = "win" if tgt == 1 else "loss" if tgt == 0 else "push"
        pnl = 1.0 if outcome == "win" else -1.0 if outcome == "loss" else 0.0
        ev_pct = ((tgt - implied_prob) * 100) if (tgt is not None and implied_prob is not None) else None
        rows.append(
            MicroModelRow(
                theory_id=None,
                game_id=gid,
                market_type="spread",
                side="home",
                closing_line=closing_line,
                closing_odds=closing_odds,
                implied_prob=implied_prob,
                final_score_home=getattr(game, "home_score", None) if game else None,
                final_score_away=getattr(game, "away_score", None) if game else None,
                outcome=outcome,
                pnl_units=pnl,
                est_ev_pct=ev_pct,
                trigger_flag=trigger_flag,
                features={k: v for k, v in row.items() if k != "game_id"},
                meta={
                    "season": getattr(game, "season", None) if game else None,
                    "game_date": getattr(game, "game_date", None).isoformat() if (game and game.game_date) else None,
                    "conference": getattr(game, "is_conference_game", None) if game else None,
                },
            )
        )
    return rows


def _compute_theory_metrics(rows: list[MicroModelRow], baseline_rows: list[MicroModelRow] | None = None) -> TheoryMetrics:
    n = len(rows)
    cover_rate = sum(1 for r in rows if r.outcome == "win") / n if n else 0.0
    base_rate = None
    if baseline_rows:
        b = len(baseline_rows)
        base_rate = sum(1 for r in baseline_rows if r.outcome == "win") / b if b else None
    delta = (cover_rate - base_rate) if base_rate is not None else None
    evs = [r.est_ev_pct for r in rows if r.est_ev_pct is not None]
    ev_vs_implied = float(np.mean(evs)) if evs else None
    pnl_curve: list[float] = []
    acc = 0.0
    for r in rows:
        acc += r.pnl_units or 0.0
        pnl_curve.append(acc)
    max_dd = None
    peak = -1e9
    for v in pnl_curve:
        peak = max(peak, v)
        dd = peak - v
        max_dd = dd if max_dd is None or dd > max_dd else max_dd
    sharpe_like = None
    pnl_changes = [r.pnl_units for r in rows if r.pnl_units is not None]
    if len(pnl_changes) > 1:
        sharpe_like = float(np.mean(pnl_changes) / (np.std(pnl_changes) + 1e-9))
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


async def _player_minutes_map(
    session: AsyncSession, game_ids: list[int], player: str | None, window: int = 5
) -> dict[int, dict[str, float | None]]:
    """Build per-game player minutes + rolling averages."""
    if not player or not game_ids:
        return {}
    stmt = (
        select(db_models.SportsGame.id, db_models.SportsGame.game_date, SportsPlayerBoxscore.stats)
        .join(SportsPlayerBoxscore, SportsPlayerBoxscore.game_id == db_models.SportsGame.id)
        .where(db_models.SportsGame.id.in_(game_ids))
        .where(func.lower(SportsPlayerBoxscore.player_name).like(f"%{player.lower()}%"))
        .order_by(db_models.SportsGame.game_date)
    )
    res = await session.execute(stmt)
    rows = res.fetchall()
    minutes_map: dict[int, dict[str, float | None]] = {}
    history: list[float] = []
    for gid, game_date, stats in rows:
        mins_val = stats.get("minutes") or stats.get("mp")
        try:
            minutes_float = float(mins_val) if mins_val is not None else None
        except (TypeError, ValueError):
            minutes_float = None
        rolling = None
        if history:
            rolling = float(statistics.mean(history[-window:]))
        delta = None
        if minutes_float is not None and rolling is not None:
            delta = minutes_float - rolling
        minutes_map[gid] = {
            "player_minutes": minutes_float,
            "player_minutes_rolling": rolling,
            "player_minutes_delta": delta,
        }
        if minutes_float is not None:
            history.append(minutes_float)
    return minutes_map


def _attach_player_minutes(feature_data: list[dict[str, Any]], minutes_map: dict[int, dict[str, float | None]]) -> None:
    if not minutes_map:
        return
    for row in feature_data:
        gid = row.get("game_id")
        if gid in minutes_map:
            row.update(minutes_map[gid])


@router.post("/preview")
async def preview_features(req: FeaturePreviewRequest, session: AsyncSession = Depends(get_db)):
    """Preview feature matrix before running analysis. Supports CSV or JSON quality summary."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)

    stmt: Select = select(db_models.SportsGame.id)
    stmt = _apply_base_filters(stmt, league, req)
    if req.offset is not None:
        stmt = stmt.offset(req.offset)
    if req.limit is not None:
        stmt = stmt.limit(req.limit)
    game_rows = await session.execute(stmt)
    all_game_ids = [row[0] for row in game_rows.fetchall()]
    all_game_ids = await _filter_games_by_player(session, all_game_ids, getattr(req, "player", None))

    if not all_game_ids:
        if req.format.lower() == "json":
            return FeaturePreviewSummary(rows_inspected=0, feature_stats={})
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["game_id", *[f.name for f in req.features]])
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, req.features, layer_builder=layer_builder
    )
    minutes_map = await _player_minutes_map(session, all_game_ids, getattr(req, "player", None))
    _attach_player_minutes(feature_data, minutes_map)
    minutes_map = await _player_minutes_map(session, all_game_ids, getattr(req, "player", None))
    _attach_player_minutes(feature_data, minutes_map)
    minutes_map = await _player_minutes_map(session, all_game_ids, getattr(req, "player", None))
    _attach_player_minutes(feature_data, minutes_map)
    minutes_map = await _player_minutes_map(session, all_game_ids, getattr(req, "player", None))
    _attach_player_minutes(feature_data, minutes_map)
    feature_names = [f.name for f in req.features if (not req.feature_filter or f.name in req.feature_filter)]
    if layer_builder and feature_data:
        layered_names = [
            k
            for k in feature_data[0].keys()
            if k not in {"game_id"} and (not req.feature_filter or k in req.feature_filter)
        ]
        feature_names = feature_names + [name for name in layered_names if name not in feature_names]

    fmt = req.format.lower()
    if fmt == "json":
        filtered_data = [
            {k: v for k, v in row.items() if (k == "game_id" or k in feature_names)} for row in feature_data
        ]
        stats = _compute_quality_stats(filtered_data, feature_names)
        items = list(stats.items())
        sort_by = (req.sort_by or "null_pct").lower()
        sort_dir = (req.sort_dir or "desc").lower()
        reverse = sort_dir != "asc"
        if sort_by == "non_numeric":
            items.sort(key=lambda kv: kv[1].non_numeric, reverse=reverse)
        elif sort_by == "name":
            items.sort(key=lambda kv: kv[0], reverse=reverse)
        else:
            items.sort(key=lambda kv: kv[1].null_pct, reverse=reverse)
        stats = {k: v for k, v in items}
        return FeaturePreviewSummary(rows_inspected=len(filtered_data), feature_stats=stats)

    # CSV path
    include_target = bool(req.include_target or req.target)
    game_to_targets: dict[int, float] = {}
    if include_target:
        stmt_games = select(db_models.SportsGame).where(db_models.SportsGame.id.in_(all_game_ids)).options(
            selectinload(db_models.SportsGame.odds),
            selectinload(db_models.SportsGame.home_team),
            selectinload(db_models.SportsGame.away_team),
        )
        games_res = await session.execute(stmt_games)
        for game in games_res.scalars().all():
            metrics = compute_derived_metrics(game, game.odds)
            tgt_val = _target_value(metrics, req.target or "")
            if tgt_val is not None:
                game_to_targets[game.id] = tgt_val

    header = ["game_id"]
    if include_target:
        header.append("target")
    header.extend(feature_names)

    def csv_iter():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for row in feature_data:
            gid = row.get("game_id")
            vals = [row.get(fname, "") for fname in feature_names]
            if include_target:
                tgt = game_to_targets.get(gid, "")
                writer.writerow([gid, tgt, *vals])
            else:
                writer.writerow([gid, *vals])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(csv_iter(), media_type="text/csv")


@router.post("/analyze", response_model=AnalysisWithMicroResponse)
async def run_analysis(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> AnalysisWithMicroResponse:
    """Run correlation analysis for generated features against a target."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)

    # Fetch game ids filtered by seasons if provided
    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    if req.games_limit:
        stmt = stmt.limit(min(req.games_limit, MAX_GAMES_LIMIT))
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]
    all_game_ids = await _filter_games_by_player(session, all_game_ids, getattr(req, "player", None))
    games = [g for g in games if g.id in all_game_ids]

    if not all_game_ids:
        return AnalysisResponse(
            sample_size=0,
            baseline_rate=0.0,
            correlations=[],
            best_segments=[],
            insights=["No games found for the selected filters."],
        )

    # Compute feature values
    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, req.features, layer_builder=layer_builder
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
        tgt_val = _target_value(metrics, req.target)
        if tgt_val is not None:
            game_to_targets[game.id] = tgt_val

    # Assemble aligned data
    feature_names = [f.name for f in req.features]
    if layer_builder and feature_data:
        layered_names = [k for k in feature_data[0].keys() if k not in {"game_id"}]
        feature_names = feature_names + [name for name in layered_names if name not in feature_names]
    aligned_features, aligned_target, kept_ids, cleaning_summary = _prepare_dataset(
        feature_data, feature_names, game_to_targets, req.cleaning
    )
    sample_size = len(aligned_target)
    if sample_size == 0:
        return AnalysisResponse(
            sample_size=0,
            baseline_rate=0.0,
            correlations=[],
            best_segments=[],
            insights=["No target values available for selected games."],
            cleaning_summary=cleaning_summary,
        )

    baseline_rate = float(np.mean(aligned_target))

    correlations: list[CorrelationResult] = []
    insights: list[str] = []

    # Drop duplicate/identical feature vectors and near-constant features to avoid skew
    usable_features: dict[str, list[float]] = {}
    seen_signatures: set[tuple] = set()
    dropped_dupe = 0
    dropped_low_var = 0
    for name, values in aligned_features.items():
        if len(values) != sample_size:
            continue
        clean_vals = [v for v in values if not np.isnan(v)]
        if len(clean_vals) < 5:
            continue
        if np.std(clean_vals) < 1e-9:  # effectively constant
            dropped_low_var += 1
            continue
        signature = tuple(None if np.isnan(v) else round(float(v), 6) for v in values)
        if signature in seen_signatures:
            dropped_dupe += 1
            continue
        seen_signatures.add(signature)
        usable_features[name] = values

    for name, values in usable_features.items():
        clean_pairs = [(x, y) for x, y in zip(values, aligned_target) if not (np.isnan(x) or np.isnan(y))]
        if len(clean_pairs) < 5:
            continue
        xs = [p[0] for p in clean_pairs]
        ys = [p[1] for p in clean_pairs]
        corr = _pearson_correlation(xs, ys)
        if corr is None:
            continue
        is_sig = abs(corr) >= 0.05
        correlations.append(CorrelationResult(feature=name, correlation=corr, p_value=None, is_significant=is_sig))
        if is_sig:
            direction = "more" if corr > 0 else "less"
            insights.append(f"{name} correlates with {req.target}: {direction} {req.target} when this increases.")

    correlations = sorted(correlations, key=lambda c: abs(c.correlation), reverse=True)[:10]

    micro_rows = _build_micro_rows(games, feature_data, kept_ids, game_to_targets, trigger_flag=True)
    theory_metrics = _compute_theory_metrics(micro_rows, None)

    return AnalysisWithMicroResponse(
        sample_size=sample_size,
        baseline_rate=baseline_rate,
        correlations=correlations,
        best_segments=[],
        insights=(
            insights[:5]
            or [
                "No strong correlations detected.",
                f"Dropped {dropped_dupe} duplicate feature vectors and {dropped_low_var} low-variance features."
                if (dropped_dupe or dropped_low_var)
                else "",
            ]
        ),
        cleaning_summary=cleaning_summary,
        micro_model_results=micro_rows,
        theory_metrics=theory_metrics,
    )


@router.post("/analyze/export")
async def export_analysis_csv(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Export the feature matrix with targets as CSV, for the same filters/features/target used in analysis."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)

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
        writer.writerow(["game_id", "target", *[f.name for f in req.features]])
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, req.features, layer_builder=layer_builder
    )

    # Fetch derived targets
    game_to_targets: dict[int, float] = {}
    stmt_games = select(db_models.SportsGame).where(db_models.SportsGame.id.in_(all_game_ids)).options(
        selectinload(db_models.SportsGame.odds),
        selectinload(db_models.SportsGame.home_team),
        selectinload(db_models.SportsGame.away_team),
    )
    games_res = await session.execute(stmt_games)
    for game in games_res.scalars().all():
        metrics = compute_derived_metrics(game, game.odds)
        tgt_val = _target_value(metrics, req.target)
        if tgt_val is not None:
            game_to_targets[game.id] = tgt_val

    feature_names = [f.name for f in req.features]
    if layer_builder and feature_data:
        layered_names = [k for k in feature_data[0].keys() if k not in {"game_id"}]
        feature_names = feature_names + [name for name in layered_names if name not in feature_names]
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

    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    if req.games_limit:
        stmt = stmt.limit(req.games_limit)
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, req.features, layer_builder=layer_builder
    )

    # targets
    game_to_targets: dict[int, float] = {}
    for game in games:
        metrics = compute_derived_metrics(game, game.odds)
        tgt_val = _target_value(metrics, req.target)
        if tgt_val is not None:
            game_to_targets[game.id] = tgt_val

    feature_names = [f.name for f in req.features]
    if layer_builder and feature_data:
        layered_names = [k for k in feature_data[0].keys() if k not in {"game_id"}]
        feature_names = feature_names + [name for name in layered_names if name not in feature_names]
    aligned_features, aligned_target, kept_ids, _summary = _prepare_dataset(
        feature_data, feature_names, game_to_targets, req.cleaning
    )
    micro_rows = _build_micro_rows(games, feature_data, kept_ids, game_to_targets, trigger_flag=True)

    def csv_iter():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "theory_id",
                "game_id",
                "market_type",
                "side",
                "closing_line",
                "closing_odds",
                "implied_prob",
                "final_score_home",
                "final_score_away",
                "outcome",
                "pnl_units",
                "est_ev_pct",
                "trigger_flag",
                *feature_names,
            ]
        )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for idx, mm in enumerate(micro_rows):
            feature_vals = []
            for fname in feature_names:
                feature_vals.append((mm.features or {}).get(fname, ""))
            writer.writerow(
                [
                    mm.theory_id or "",
                    mm.game_id,
                    mm.market_type,
                    mm.side,
                    mm.closing_line or "",
                    mm.closing_odds or "",
                    mm.implied_prob or "",
                    mm.final_score_home or "",
                    mm.final_score_away or "",
                    mm.outcome or "",
                    mm.pnl_units or "",
                    mm.est_ev_pct or "",
                    mm.trigger_flag,
                    *feature_vals,
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(csv_iter(), media_type="text/csv")


@router.post("/build-model", response_model=ModelBuildWithMicroResponse)
async def build_model(req: ModelBuildRequest, session: AsyncSession = Depends(get_db)) -> ModelBuildWithMicroResponse:
    """Train a lightweight model on the computed features and return suggested theories."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)

    stmt: Select = select(db_models.SportsGame)
    stmt = _apply_base_filters(stmt, league, req)
    game_rows = await session.execute(stmt)
    games = game_rows.scalars().unique().all()
    all_game_ids = [g.id for g in games]

    if not all_game_ids:
        return ModelBuildWithMicroResponse(
            model_summary=TrainedModelResponse(
                model_type="logistic_regression",
                features_used=[],
                feature_weights={},
                accuracy=0.0,
                roi=0.0,
            ),
            suggested_theories=[],
            validation_stats={},
        )

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, req.features, layer_builder=layer_builder
    )

    # target values
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
    game_to_target: dict[int, float] = {}
    for game in games_res.scalars().all():
        metrics = compute_derived_metrics(game, game.odds)
        tgt_val = _target_value(metrics, req.target)
        if tgt_val is not None:
            game_to_target[game.id] = tgt_val

    feature_names = [f.name for f in req.features]
    if layer_builder and feature_data:
        layered_names = [k for k in feature_data[0].keys() if k not in {"game_id"}]
        feature_names = feature_names + [name for name in layered_names if name not in feature_names]
    aligned_features, aligned_target, kept_ids, cleaning_summary = _prepare_dataset(
        feature_data, feature_names, game_to_target, req.cleaning
    )

    aligned_rows: list[dict[str, float]] = []
    for idx in range(len(aligned_target)):
        entry: dict[str, float] = {"__target__": aligned_target[idx]}
        for fname in feature_names:
            val = aligned_features[fname][idx]
            entry[fname] = 0.0 if (val is None or np.isnan(val)) else float(val)
        aligned_rows.append(entry)

    trained = train_logistic_regression(aligned_rows, feature_names, "__target__")

    # Use previous analysis correlations if available; otherwise empty
    correlations: list[CorrelationResult] = []
    suggested = generate_theories(trained, correlations, [])

    micro_rows = _build_micro_rows(games, feature_data, kept_ids, game_to_target, trigger_flag=True)
    theory_metrics = _compute_theory_metrics(micro_rows, None)
    mc_summary = simulate_historical_mc(micro_rows)

    return ModelBuildWithMicroResponse(
        model_summary=TrainedModelResponse(
            model_type=trained.model_type,
            features_used=trained.features_used,
            feature_weights=trained.feature_weights,
            accuracy=trained.accuracy,
            roi=trained.roi,
        ),
        suggested_theories=[
          SuggestedTheoryResponse(
              text=t.text,
              features_used=t.features_used,
              historical_edge=t.historical_edge,
              confidence=t.confidence,
          )
          for t in suggested
        ],
        validation_stats={"accuracy": trained.accuracy, "roi": trained.roi},
        cleaning_summary=cleaning_summary,
        micro_model_results=micro_rows,
        theory_metrics=theory_metrics,
        mc_summary=mc_summary,
    )


