"""Theory run pipeline endpoints (v1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from .. import db_models
from ..services.llm_prompt_grading import grade_prompt
from ..services.llm_config_inference import infer_model_config
from ..services.model_config_builder import build_model_config
from ..services.historical_data import get_historical_games
from ..services.theory_filters import apply_theory_filters
from ..services.historical_performance import compute_historical_performance
from ..services.backtest import run_30day_backtest
from ..services.monte_carlo import run_monte_carlo
from ..services.llm_summary import generate_summary
from ..services.bet_performance import StoredBetRow
from ..logging_config import get_logger

router = APIRouter(prefix="/api/theory-runs", tags=["theory-runs"])

logger = get_logger(__name__)


class TheoryRunRequest(BaseModel):
    sport: str
    theory_text: str
    user_stats: list[str] | None = None
    user_bet_types: list[str] | None = None


class TheoryRunResult(BaseModel):
    run_id: str
    sport: str
    theory_text: str
    summary: str
    prompt_feedback: list[str]
    bet_performance_by_type: list[Any]
    upcoming_bets: list[Any]
    stat_drivers: list[Any]
    model_explanation: str
    meta: dict


@router.post("", response_model=TheoryRunResult)
async def create_theory_run(payload: TheoryRunRequest, session: AsyncSession = Depends(get_db)) -> TheoryRunResult:
    """Create a theory run and execute the v1 pipeline."""
    try:
        # 1) Prompt grading
        prompt_grade = grade_prompt(payload.theory_text, payload.sport)

        # 2) Config inference
        inferred_cfg = infer_model_config(payload.theory_text, payload.sport)
        inferred_cfg["sport"] = payload.sport

        user_overrides = {
            "features": payload.user_stats,
            "bet_types": payload.user_bet_types,
        }
        model_config = build_model_config(inferred_cfg, user_overrides)
        bet_types = model_config.get("bet_types") or ["spread"]

        # 3) Historical data
        historical = await get_historical_games(
            session=session,
            sport=payload.sport,
            seasons=model_config.get("historical_seasons", []),
            last_n_days=model_config.get("backtest_window_days", 30) + 365,  # 2 seasons approx
        )

        # 4) Apply filters -> StoredBetRow list
        bet_rows = await apply_theory_filters(session, historical, model_config)

        # 5) Historical performance + backtest
        hist_perf = compute_historical_performance(bet_rows, bet_types)
        backtest_perf = run_30day_backtest(bet_rows, bet_types)

        # 6) Upcoming bets (stub via Monte Carlo)
        upcoming_bets = run_monte_carlo([], model_config)

        # 7) Summary via LLM
        model_results = {
            "historical": [p.model_dump() for p in hist_perf],
            "backtest": {k: v.model_dump() for k, v in backtest_perf.items()},
            "upcoming_bets": upcoming_bets,
        }
        summary_bundle = generate_summary(model_results, payload.theory_text)

        result_payload = TheoryRunResult(
            run_id="",
            sport=payload.sport,
            theory_text=payload.theory_text,
            summary=summary_bundle.get("summary", ""),
            prompt_feedback=summary_bundle.get("prompt_feedback", prompt_grade.get("suggestions", [])),
            bet_performance_by_type=[p.model_dump() for p in hist_perf],
            upcoming_bets=upcoming_bets,
            stat_drivers=summary_bundle.get("stat_drivers", []),
            model_explanation=summary_bundle.get("model_explanation", ""),
            meta={"created_at": datetime.utcnow().isoformat(), "version": "v1"},
        )

        # 8) Persist TheoryRun
        run_row = db_models.TheoryRun(
            sport=payload.sport,
            theory_text=payload.theory_text,
            model_config=model_config,
            results=result_payload.model_dump(),
            status="completed",
            completed_at=datetime.utcnow(),
        )
        session.add(run_row)
        await session.commit()
        await session.refresh(run_row)

        result_payload.run_id = str(run_row.id)
        return result_payload
    except Exception as exc:  # pragma: no cover
        logger.error("theory_run_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{run_id}", response_model=TheoryRunResult)
async def get_theory_run(run_id: int, session: AsyncSession = Depends(get_db)) -> TheoryRunResult:
    run = await session.get(db_models.TheoryRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    data = run.results or {}
    data["run_id"] = str(run.id)
    return TheoryRunResult(**data)

