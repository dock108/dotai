"""Admin endpoints for managing sports modeling / EDA configurations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, desc, select

from .. import db_models
from ..db import AsyncSession, get_db

router = APIRouter(prefix="/api/admin/sports/models", tags=["sports-models"])


class SportsModelConfigCreate(BaseModel):
  """Payload for creating a new sports model config."""

  model_config = ConfigDict(populate_by_name=True)

  league_code: str = Field(..., alias="leagueCode")
  name: str
  description: str | None = None
  config: dict[str, Any] = Field(
      default_factory=dict,
      description="Arbitrary modeling config JSON (filters, features, targets, etc.).",
  )


class SportsModelConfigResponse(BaseModel):
  id: int
  league_code: str
  name: str
  description: str | None
  status: str
  config: dict[str, Any]
  created_at: datetime
  updated_at: datetime


async def _get_league(session: AsyncSession, code: str) -> db_models.SportsLeague:
  stmt = select(db_models.SportsLeague).where(db_models.SportsLeague.code == code.upper())
  result = await session.execute(stmt)
  league = result.scalar_one_or_none()
  if not league:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"League {code} not found")
  return league


def _serialize_model_config(
  cfg: db_models.SportsModelConfig, league_code: str
) -> SportsModelConfigResponse:
  return SportsModelConfigResponse(
      id=cfg.id,
      league_code=league_code,
      name=cfg.name,
      description=cfg.description,
      status=cfg.status,
      config=cfg.config,
      created_at=cfg.created_at,
      updated_at=cfg.updated_at,
  )


@router.post("", response_model=SportsModelConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_model_config(
  payload: SportsModelConfigCreate,
  session: AsyncSession = Depends(get_db),
) -> SportsModelConfigResponse:
  """Create a new sports model configuration.

  For now this is a thin wrapper that stores arbitrary JSON; future
  iterations can validate the config structure more strictly.
  """
  league = await _get_league(session, payload.league_code)
  cfg = db_models.SportsModelConfig(
      league_id=league.id,
      name=payload.name,
      description=payload.description,
      status="draft",
      config=payload.config,
  )
  session.add(cfg)
  await session.commit()
  await session.refresh(cfg)
  return _serialize_model_config(cfg, league.code)


@router.get("", response_model=list[SportsModelConfigResponse])
async def list_model_configs(
  session: AsyncSession = Depends(get_db),
  league: str | None = Query(None),
  status_filter: str | None = Query(None, alias="status"),
) -> list[SportsModelConfigResponse]:
  """List stored model configurations, optionally filtered by league/status."""
  stmt: Select = select(db_models.SportsModelConfig).join(db_models.SportsLeague)
  if league:
      stmt = stmt.where(db_models.SportsLeague.code == league.upper())
  if status_filter:
      stmt = stmt.where(db_models.SportsModelConfig.status == status_filter)
  stmt = stmt.order_by(desc(db_models.SportsModelConfig.created_at))
  results = await session.execute(stmt)
  configs: list[db_models.SportsModelConfig] = results.scalars().all()
  return [
      _serialize_model_config(cfg, cfg.league.code if cfg.league else "UNKNOWN")
      for cfg in configs
  ]


@router.post("/{config_id}/activate", response_model=SportsModelConfigResponse)
async def activate_model_config(
  config_id: int,
  session: AsyncSession = Depends(get_db),
) -> SportsModelConfigResponse:
  """Mark a model config as active for its league (single active per league)."""
  cfg = await session.get(db_models.SportsModelConfig, config_id)
  if not cfg:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model config not found")

  # Deactivate existing active configs for this league
  stmt = select(db_models.SportsModelConfig).where(
      db_models.SportsModelConfig.league_id == cfg.league_id,
      db_models.SportsModelConfig.status == "active",
  )
  existing = (await session.execute(stmt)).scalars().all()
  for other in existing:
      other.status = "deprecated"

  cfg.status = "active"
  await session.commit()
  await session.refresh(cfg)
  league_code = cfg.league.code if cfg.league else "UNKNOWN"
  return _serialize_model_config(cfg, league_code)


