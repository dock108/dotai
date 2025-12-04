"""Admin endpoints for viewing theory evaluation requests and their processing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import selectinload

from .. import db_models
from ..db import AsyncSession, get_db

router = APIRouter(prefix="/api/admin/theories", tags=["admin-theories"])


class TheoryRequestResponse(BaseModel):
    """Response model for a theory request with optional evaluation."""

    id: int
    domain: str
    raw_text: str
    normalized_text: str | None
    created_at: datetime
    user_id: int | None
    evaluation: dict[str, Any] | None = None


class TheoryRequestsListResponse(BaseModel):
    """Response for listing theory requests."""

    requests: list[TheoryRequestResponse]
    total: int
    next_offset: int | None


@router.get("", response_model=TheoryRequestsListResponse)
async def list_theory_requests(
    domain: str | None = Query(None, description="Filter by domain (bets, crypto, stocks, etc.)"),
    limit: int = Query(50, ge=1, le=200, description="Number of requests to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db),
) -> TheoryRequestsListResponse:
    """List theory evaluation requests with their derived processing and evaluation results.
    
    This endpoint allows admins to trace user requests from the main portal,
    see the original request, normalized/derived version, and evaluation results.
    """
    stmt: Select = select(db_models.Theory).options(
        selectinload(db_models.Theory.evaluations)
    )
    
    if domain:
        stmt = stmt.where(db_models.Theory.domain == domain)
    
    # Count total
    count_stmt: Select = select(func.count(db_models.Theory.id))
    if domain:
        count_stmt = count_stmt.where(db_models.Theory.domain == domain)
    total = (await session.execute(count_stmt)).scalar_one()
    
    # Get paginated results
    stmt = stmt.order_by(desc(db_models.Theory.created_at)).offset(offset).limit(limit)
    results = await session.execute(stmt)
    theories: list[db_models.Theory] = results.scalars().unique().all()
    
    requests: list[TheoryRequestResponse] = []
    for theory in theories:
        # Get the most recent evaluation if any
        evaluation_data = None
        if theory.evaluations:
            # Evaluations are already loaded via selectinload
            latest_eval = max(theory.evaluations, key=lambda e: e.created_at)
            evaluation_data = {
                "id": latest_eval.id,
                "verdict": latest_eval.verdict,
                "confidence": latest_eval.confidence,
                "reasoning": latest_eval.reasoning,
                "created_at": latest_eval.created_at.isoformat(),
            }
        
        requests.append(
            TheoryRequestResponse(
                id=theory.id,
                domain=theory.domain,
                raw_text=theory.raw_text,
                normalized_text=theory.normalized_text,
                created_at=theory.created_at,
                user_id=theory.user_id,
                evaluation=evaluation_data,
            )
        )
    
    next_offset = offset + limit if offset + limit < total else None
    
    return TheoryRequestsListResponse(
        requests=requests,
        total=total,
        next_offset=next_offset,
    )


@router.get("/{theory_id}", response_model=TheoryRequestResponse)
async def get_theory_request(
    theory_id: int,
    session: AsyncSession = Depends(get_db),
) -> TheoryRequestResponse:
    """Get a single theory request with full evaluation details."""
    stmt = select(db_models.Theory).options(
        selectinload(db_models.Theory.evaluations)
    ).where(db_models.Theory.id == theory_id)
    
    result = await session.execute(stmt)
    theory = result.scalar_one_or_none()
    
    if not theory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theory request {theory_id} not found",
        )
    
    evaluation_data = None
    if theory.evaluations:
        latest_eval = max(theory.evaluations, key=lambda e: e.created_at)
        evaluation_data = {
            "id": latest_eval.id,
            "verdict": latest_eval.verdict,
            "confidence": latest_eval.confidence,
            "reasoning": latest_eval.reasoning,
            "created_at": latest_eval.created_at.isoformat(),
        }
    
    return TheoryRequestResponse(
        id=theory.id,
        domain=theory.domain,
        raw_text=theory.raw_text,
        normalized_text=theory.normalized_text,
        created_at=theory.created_at,
        user_id=theory.user_id,
        evaluation=evaluation_data,
    )

