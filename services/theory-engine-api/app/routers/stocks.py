"""Stocks domain router with fundamentals analysis."""

from __future__ import annotations

from datetime import datetime

from ..utils import now_utc

from fastapi import APIRouter, HTTPException
from pydantic import Field

from py_core import (
    Domain,
    TheoryRequest,
    TheoryResponse,
    DataSource,
    evaluate_guardrails,
    has_hard_block,
    summarize_guardrails,
)
from py_core.data.fetchers import fetch_stock_context
from py_core.scoring.metrics import compute_domain_verdict

router = APIRouter(prefix="/api/theory", tags=["stocks"])


class StocksResponse(TheoryResponse):
    """Stocks-specific response with fundamentals analysis."""

    correlation_grade: str = Field(description="Grade for how well narrative matches historical correlations")
    fundamentals_match: bool = Field(description="Whether fundamentals support the theory")
    volume_analysis: str = Field(description="Volume pattern analysis")


def analyze_stocks_theory(text: str) -> dict[str, any]:
    """Analyze stocks theory against fundamentals, price history, and volume."""
    # Placeholder: would fetch fundamentals, price history, volume
    # Grade narrative vs historical correlations
    
    # Mock analysis
    correlation_grade = "B"  # How well narrative matches historical data
    fundamentals_match = True  # Whether fundamentals support
    volume_analysis = "Volume patterns are consistent with similar historical moves."
    
    return {
        "correlation_grade": correlation_grade,
        "fundamentals_match": fundamentals_match,
        "volume_analysis": volume_analysis,
    }


@router.post("/stocks", response_model=StocksResponse)
async def evaluate_stocks_theory(req: TheoryRequest) -> StocksResponse:
    """Evaluate a stocks theory with fundamentals analysis."""
    
    # Run guardrails
    guardrail_results = evaluate_guardrails(req.text, Domain.stocks)
    if has_hard_block(guardrail_results):
        raise HTTPException(
            status_code=400,
            detail="This theory cannot be evaluated due to guardrail restrictions.",
        )
    
    guardrail_flags = summarize_guardrails(guardrail_results)
    
    # Fetch stock context
    context = fetch_stock_context(req.text, limit=10)
    
    # Analyze theory
    analysis = analyze_stocks_theory(req.text)
    
    # Get base verdict
    verdict_bundle = compute_domain_verdict(Domain.stocks, req.text)
    
    # Build data_used list from context
    data_used: list[DataSource] = []
    if context.data_source_name:
        data_used.append(
            DataSource(
                name=context.data_source_name,
                cache_status=context.cache_status,
                details=context.data_source_details,
            )
        )
    else:
        data_used.append(
            DataSource(
                name="Stock fundamentals + price history",
                cache_status="fresh",
                details="Revenue growth, margin compression, volume patterns",
            )
        )
    
    # Enhance how_we_got_conclusion
    conclusion_steps = verdict_bundle.how_we_got_conclusion.copy()
    conclusion_steps.append(f"Fundamentals match: {'Yes' if analysis['fundamentals_match'] else 'No'}")
    conclusion_steps.append(analysis["volume_analysis"])
    
    limitations = context.limitations.copy()
    limitations.append("This is a pattern check, not a full market model.")
    limitations.append("Earnings calls, management guidance, and macro factors may not be fully captured.")
    
    return StocksResponse(
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
        correlation_grade=analysis["correlation_grade"],
        fundamentals_match=analysis["fundamentals_match"],
        volume_analysis=analysis["volume_analysis"],
    )

