"""Admin EDA endpoints for sports data.

These endpoints power internal exploratory analysis and will eventually
serve as the backbone modeling interface for matchup evaluation and
simulations. They are **admin-only** and are not exposed to end users.
"""

from __future__ import annotations

from datetime import datetime
import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Select, func, select, text
from sqlalchemy.orm import selectinload, aliased

from .. import db_models
from ..db import AsyncSession, get_db
import numpy as np

from ..services.derived_metrics import compute_derived_metrics
from ..services.feature_compute import compute_features_for_games
from ..services.feature_engine import GeneratedFeature as GeneratedFeatureDTO, generate_features, summarize_features
from ..services.model_builder import TrainedModel, train_logistic_regression
from ..services.theory_generator import SuggestedTheory, generate_theories

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
    start_date: datetime | None = None
    end_date: datetime | None = None
    team: str | None = None
    limit: int | None = None
    offset: int | None = None
    target: str | None = None  # optional target for CSV export
    include_target: bool = False
    format: str = "csv"  # "csv" | "json"
    sort_by: str | None = None  # "null_pct" | "non_numeric" | "name"
    sort_dir: str | None = None  # "asc" | "desc"
    feature_filter: list[str] | None = None


class AnalysisRequest(BaseModel):
    league_code: str
    features: list[GeneratedFeature]
    target: str  # "cover" | "win" | "over"
    seasons: list[int] | None = None
    cleaning: CleaningOptions | None = None


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
    target: str
    seasons: list[int] | None = None
    cleaning: CleaningOptions | None = None


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


async def _get_league(session: AsyncSession, code: str) -> db_models.SportsLeague:
    stmt = select(db_models.SportsLeague).where(db_models.SportsLeague.code == code.upper())
    result = await session.execute(stmt)
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"League {code} not found")
    return league


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


@router.post("/preview")
async def preview_features(req: FeaturePreviewRequest, session: AsyncSession = Depends(get_db)):
    """Preview feature matrix before running analysis. Supports CSV or JSON quality summary."""
    league = await _get_league(session, req.league_code)

    stmt: Select = select(db_models.SportsGame.id).where(db_models.SportsGame.league_id == league.id)
    if req.seasons:
        stmt = stmt.where(db_models.SportsGame.season.in_(req.seasons))
    if req.start_date:
        stmt = stmt.where(db_models.SportsGame.game_date >= req.start_date)
    if req.end_date:
        stmt = stmt.where(db_models.SportsGame.game_date <= req.end_date)
    if req.team:
        away_team = aliased(db_models.SportsTeam)
        stmt = stmt.join(db_models.SportsTeam, db_models.SportsGame.home_team_id == db_models.SportsTeam.id, isouter=True)
        stmt = stmt.join(away_team, db_models.SportsGame.away_team_id == away_team.id, isouter=True)
        team_filter = f"%{req.team.lower()}%"
        stmt = stmt.where(
            func.lower(db_models.SportsTeam.name).like(team_filter)
            | func.lower(db_models.SportsTeam.short_name).like(team_filter)
            | func.lower(db_models.SportsTeam.abbreviation).like(team_filter)
            | func.lower(away_team.name).like(team_filter)
            | func.lower(away_team.short_name).like(team_filter)
            | func.lower(away_team.abbreviation).like(team_filter)
        )
    if req.offset is not None:
        stmt = stmt.offset(req.offset)
    if req.limit is not None:
        stmt = stmt.limit(req.limit)
    game_rows = await session.execute(stmt)
    all_game_ids = [row[0] for row in game_rows.fetchall()]

    if not all_game_ids:
        if req.format.lower() == "json":
            return FeaturePreviewSummary(rows_inspected=0, feature_stats={})
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["game_id", *[f.name for f in req.features]])
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")

    feature_data = await compute_features_for_games(session, league.id, all_game_ids, req.features)
    feature_names = [f.name for f in req.features if (not req.feature_filter or f.name in req.feature_filter)]

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


@router.post("/analyze", response_model=AnalysisResponse)
async def run_analysis(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> AnalysisResponse:
    """Run correlation analysis for generated features against a target."""
    league = await _get_league(session, req.league_code)

    # Fetch game ids filtered by seasons if provided
    stmt: Select = select(db_models.SportsGame.id, db_models.SportsGame.season).where(db_models.SportsGame.league_id == league.id)
    if req.seasons:
        stmt = stmt.where(db_models.SportsGame.season.in_(req.seasons))
    game_rows = await session.execute(stmt)
    all_game_ids = [row[0] for row in game_rows.fetchall()]

    if not all_game_ids:
        return AnalysisResponse(
            sample_size=0,
            baseline_rate=0.0,
            correlations=[],
            best_segments=[],
            insights=["No games found for the selected filters."],
        )

    # Compute feature values
    feature_data = await compute_features_for_games(session, league.id, all_game_ids, req.features)

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

    return AnalysisResponse(
        sample_size=sample_size,
        baseline_rate=baseline_rate,
        correlations=correlations,
        best_segments=[],  # Placeholder for future segment discovery
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
    )


@router.post("/analyze/export")
async def export_analysis_csv(req: AnalysisRequest, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Export the feature matrix with targets as CSV, for the same filters/features/target used in analysis."""
    league = await _get_league(session, req.league_code)

    stmt: Select = select(db_models.SportsGame.id).where(db_models.SportsGame.league_id == league.id)
    if req.seasons:
        stmt = stmt.where(db_models.SportsGame.season.in_(req.seasons))
    game_rows = await session.execute(stmt)
    all_game_ids = [row[0] for row in game_rows.fetchall()]

    if not all_game_ids:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["game_id", "target", *[f.name for f in req.features]])
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")

    feature_data = await compute_features_for_games(session, league.id, all_game_ids, req.features)

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


@router.post("/build-model", response_model=ModelBuildResponse)
async def build_model(req: ModelBuildRequest, session: AsyncSession = Depends(get_db)) -> ModelBuildResponse:
    """Train a lightweight model on the computed features and return suggested theories."""
    league = await _get_league(session, req.league_code)

    stmt: Select = select(db_models.SportsGame.id, db_models.SportsGame.season).where(db_models.SportsGame.league_id == league.id)
    if req.seasons:
        stmt = stmt.where(db_models.SportsGame.season.in_(req.seasons))
    game_rows = await session.execute(stmt)
    all_game_ids = [row[0] for row in game_rows.fetchall()]

    if not all_game_ids:
        return ModelBuildResponse(
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

    feature_data = await compute_features_for_games(session, league.id, all_game_ids, req.features)

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

    return ModelBuildResponse(
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
    )


