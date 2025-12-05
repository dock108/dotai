"""Admin endpoints for listing and inspecting theory runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Select, desc, func, select

from .. import db_models
from ..db import AsyncSession, get_db

router = APIRouter(prefix="/api/admin/theory-runs", tags=["admin-theory-runs"])


class TheoryRunListItem(BaseModel):
    id: int
    sport: str
    theory_text: str
    status: str
    created_at: datetime
    completed_at: datetime | None


class TheoryRunsListResponse(BaseModel):
    runs: list[TheoryRunListItem]
    total: int
    next_offset: int | None


class TheoryRunAdminResponse(BaseModel):
    id: int
    sport: str
    theory_text: str
    status: str
    run_config: dict[str, Any]
    results: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None


@router.get("", response_model=TheoryRunsListResponse)
async def list_theory_runs(
    sport: str | None = Query(None, description="Filter by sport code"),
    status: str | None = Query(None, description="Filter by run status"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db),
) -> TheoryRunsListResponse:
    stmt: Select = select(db_models.TheoryRun)
    if sport:
        stmt = stmt.where(db_models.TheoryRun.sport == sport)
    if status:
        stmt = stmt.where(db_models.TheoryRun.status == status)

    count_stmt: Select = select(func.count(db_models.TheoryRun.id))
    if sport:
        count_stmt = count_stmt.where(db_models.TheoryRun.sport == sport)
    if status:
        count_stmt = count_stmt.where(db_models.TheoryRun.status == status)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(desc(db_models.TheoryRun.created_at)).offset(offset).limit(limit)
    result = await session.execute(stmt)
    runs = result.scalars().all()

    items = [
        TheoryRunListItem(
            id=r.id,
            sport=r.sport,
            theory_text=r.theory_text[:240],
            status=r.status,
            created_at=r.created_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]
    next_offset = offset + limit if len(items) == limit else None
    return TheoryRunsListResponse(runs=items, total=total, next_offset=next_offset)


@router.get("/{run_id}", response_model=TheoryRunAdminResponse)
async def get_theory_run_admin(run_id: int, session: AsyncSession = Depends(get_db)) -> TheoryRunAdminResponse:
    run = await session.get(db_models.TheoryRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return TheoryRunAdminResponse(
        id=run.id,
        sport=run.sport,
        theory_text=run.theory_text,
        status=run.status,
        run_config=run.model_config,
        results=run.results,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )

