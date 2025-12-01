"""Bets domain router with odds analysis and edge estimation."""

from __future__ import annotations

from datetime import datetime

from ..utils import now_utc

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from py_core import (
    Domain,
    TheoryRequest,
    TheoryResponse,
    DataSource,
    evaluate_guardrails,
    has_hard_block,
    summarize_guardrails,
)
from py_core.data.fetchers import fetch_odds_context
from py_core.scoring.metrics import compute_domain_verdict

router = APIRouter(prefix="/api/theory", tags=["bets"])


class BetsRequest(TheoryRequest):
    """Extended request for bets domain."""

    sport: str | None = Field(default=None, description="Sport (e.g., MLB, NBA, NFL)")
    league: str | None = Field(default=None, description="League name")
    horizon: str | None = Field(default="single_game", description="single_game or full_season")


class BetsResponse(TheoryResponse):
    """Bets-specific response with edge estimates."""

    likelihood_grade: str = Field(description="A-F grade for likelihood")
    edge_estimate: float | None = Field(default=None, description="Estimated edge if calculable")
    kelly_sizing_example: str = Field(description="Long-term outcome with Kelly-lite sizing")


def analyze_bets_theory(text: str, sport: str | None, horizon: str | None) -> dict[str, any]:
    """Analyze betting theory against historical odds and results."""
    # Placeholder: would fetch historical odds + results
    # Compare theory to actual hit rates / implied probabilities
    
    # Mock analysis
    likelihood_grade = "C"  # Would be calculated from historical data
    edge_estimate = 0.02  # 2% edge if calculable
    
    # Kelly-lite sizing example
    kelly_example = (
        "If you bet $100 per game with Kelly-lite sizing (2% of bankroll), "
        "over 100 games you'd expect: +$200 profit (2% edge × 100 games), "
        "with a standard deviation of ±$1,000. This is a distribution, not a guarantee."
    )
    
    return {
        "likelihood_grade": likelihood_grade,
        "edge_estimate": edge_estimate,
        "kelly_sizing_example": kelly_example,
    }


@router.post("/bets", response_model=BetsResponse)
async def evaluate_bets_theory(req: BetsRequest) -> BetsResponse:
    """Evaluate a betting theory with odds analysis."""
    
    # Run guardrails
    guardrail_results = evaluate_guardrails(req.text, Domain.bets)
    if has_hard_block(guardrail_results):
        raise HTTPException(
            status_code=400,
            detail="This theory cannot be evaluated due to guardrail restrictions.",
        )
    
    guardrail_flags = summarize_guardrails(guardrail_results)
    
    # Fetch odds context
    context = fetch_odds_context(req.text, limit=10)
    
    # Analyze theory
    analysis = analyze_bets_theory(req.text, req.sport, req.horizon)
    
    # Get base verdict
    verdict_bundle = compute_domain_verdict(Domain.bets, req.text)
    
    # Build data_used list from context
    data_used: list[DataSource] = []
    if context.data_source_name:
        data_used.append(
            DataSource(
                name=context.data_source_name,
                cache_status=context.cache_status,
                details=context.data_source_details or f"{req.sport or 'all sports'}, {req.horizon or 'single_game'}",
            )
        )
    else:
        data_used.append(
            DataSource(
                name=f"Historical odds + results ({req.sport or 'all sports'}, {req.horizon or 'single_game'})",
                cache_status="cached" if "cache" in str(context.sources).lower() else "fresh",
                details="Play-by-play for 2023-2024 NFL regular season" if req.sport == "NFL" else None,
            )
        )
    
    # Enhance how_we_got_conclusion with analysis details
    conclusion_steps = verdict_bundle.how_we_got_conclusion.copy()
    conclusion_steps.append(f"Historical analysis grade: {analysis['likelihood_grade']}")
    if analysis["edge_estimate"]:
        conclusion_steps.append(f"Estimated edge: {analysis['edge_estimate']:.1%}")
    
    limitations = context.limitations.copy()
    limitations.append("This is a pattern check, not a full market model.")
    limitations.append("Odds data may not include all books or closing line value.")
    
    return BetsResponse(
        summary=verdict_bundle.summary,
        verdict=verdict_bundle.verdict,
        confidence=verdict_bundle.confidence,
        data_used=data_used,
        how_we_got_conclusion=conclusion_steps,
        long_term_outcome_example=verdict_bundle.long_term_example,
        limitations=limitations,
        guardrail_flags=guardrail_flags,
        model_version="gpt-4o-mini",
        evaluation_date=now_utc().isoformat(),
        likelihood_grade=analysis["likelihood_grade"],
        edge_estimate=analysis["edge_estimate"],
        kelly_sizing_example=analysis["kelly_sizing_example"],
    )

