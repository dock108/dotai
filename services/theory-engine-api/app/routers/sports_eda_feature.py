"""Feature generation and preview endpoints for EDA."""
from __future__ import annotations

import csv
import io
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from sqlalchemy import Select, select

from .. import db_models
from ..db import AsyncSession, get_db
from ..services.feature_compute import compute_features_for_games
from ..services.feature_engine import generate_features, summarize_features
from .sports_eda_helpers import (
    _resolve_layer_builder,
    _get_league,
    _feature_policy_report,
)
from .sports_eda_schemas import (
    FeatureGenerationRequest,
    GeneratedFeature,
    FeatureGenerationResponse,
    FeaturePreviewRequest,
    FeaturePreviewSummary,
    FeatureQualityStats,
)
from .sports_eda_shared import (
    _apply_base_filters,
    _filter_games_by_player,
    _compute_quality_stats,
    _coerce_numeric,
)

router = APIRouter(prefix="/api/admin/sports/eda", tags=["sports-eda"])


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
    """Get available team and player stat keys for a given league."""
    from sqlalchemy import text

    league = await _get_league(session, league_code)

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
            timing=getattr(f, "timing", None).value if getattr(f, "timing", None) is not None else None,
            source=getattr(f, "source", None).value if getattr(f, "source", None) is not None else None,
            group=getattr(f, "group", None),
            default_selected=getattr(f, "default_selected", True),
        )
        for f in generated
    ]
    return FeatureGenerationResponse(
        features=features,
        summary=summarize_features(generated, req.raw_stats, req.include_rest_days),
    )


@router.post("/preview")
async def preview_features(req: FeaturePreviewRequest, session: AsyncSession = Depends(get_db)):
    """Preview feature matrix before running analysis. Supports CSV or JSON quality summary."""
    league = await _get_league(session, req.league_code)
    layer_builder = _resolve_layer_builder(req.feature_mode)
    filtered_features, _policy = _feature_policy_report(req.features, req.context)

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
        writer.writerow(["game_id", *[f.name for f in filtered_features]])
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")

    feature_data = await compute_features_for_games(
        session, league.id, all_game_ids, filtered_features, layer_builder=layer_builder, context=req.context
    )

    if req.format.lower() == "json":
        feature_names = [f.name for f in filtered_features]
        stats = _compute_quality_stats(feature_data, feature_names)
        return FeaturePreviewSummary(rows_inspected=len(feature_data), feature_stats=stats)

    feature_names = [f.name for f in filtered_features]
    target_name = None
    if req.target_definition:
        target_name = req.target_definition.target_name

    def csv_iter():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        header = ["game_id", *feature_names]
        if target_name:
            header.append(target_name)
        writer.writerow(header)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for row in feature_data:
            vals = [row.get("game_id")]
            for fname in feature_names:
                v = row.get(fname)
                if v is None:
                    vals.append("")
                else:
                    vals.append(v)
            if target_name:
                vals.append(row.get(target_name, ""))
            writer.writerow(vals)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(csv_iter(), media_type="text/csv")

