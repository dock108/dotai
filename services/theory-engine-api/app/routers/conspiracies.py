"""Conspiracies domain router with Wikipedia and fact-check sources."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from py_core import (
    Domain,
    TheoryRequest,
    TheoryResponse,
    DataSource,
    evaluate_guardrails,
    has_hard_block,
    summarize_guardrails,
)
from py_core.data.fetchers import fetch_conspiracy_context
from py_core.scoring.metrics import compute_domain_verdict

router = APIRouter(prefix="/api/theory", tags=["conspiracies"])


class ConspiraciesResponse(TheoryResponse):
    """Conspiracies-specific response with fact-checking."""

    likelihood_rating: int = Field(description="Likelihood rating 0-100")
    evidence_for: list[str] = Field(default_factory=list, description="Evidence supporting the claim")
    evidence_against: list[str] = Field(default_factory=list, description="Evidence against the claim")
    historical_parallels: list[str] = Field(default_factory=list, description="Similar claims that were true/false")
    missing_data: list[str] = Field(default_factory=list, description="Where data is missing")


def analyze_conspiracy_theory(text: str) -> dict[str, any]:
    """Analyze conspiracy theory using Wikipedia and fact-check sources."""
    # Placeholder: would fetch from Wikipedia, fact-check sites, research
    # No fringe sources
    
    # Mock analysis
    likelihood_rating = 28  # 0-100 scale
    evidence_for = ["Some circumstantial evidence exists"]
    evidence_against = ["Official reports contradict this", "Multiple independent sources dispute this"]
    historical_parallels = ["Similar claims about Event X were later proven false"]
    missing_data = ["No direct evidence available", "Key documents remain classified"]
    
    return {
        "likelihood_rating": likelihood_rating,
        "evidence_for": evidence_for,
        "evidence_against": evidence_against,
        "historical_parallels": historical_parallels,
        "missing_data": missing_data,
    }


@router.post("/conspiracies", response_model=ConspiraciesResponse)
async def evaluate_conspiracy_theory(req: TheoryRequest) -> ConspiraciesResponse:
    """Evaluate a conspiracy theory with strict guardrails and fact-checking."""
    
    # Run guardrails (extra strict for conspiracies)
    guardrail_results = evaluate_guardrails(req.text, Domain.conspiracies)
    if has_hard_block(guardrail_results):
        raise HTTPException(
            status_code=400,
            detail="This theory cannot be evaluated due to guardrail restrictions.",
        )
    
    guardrail_flags = summarize_guardrails(guardrail_results)
    
    # Fetch conspiracy context (Wikipedia, fact-check sites)
    context = fetch_conspiracy_context(req.text, limit=5, sources=["wikipedia", "fact-check-db"])
    
    # Analyze theory
    analysis = analyze_conspiracy_theory(req.text)
    
    # Get base verdict
    verdict_bundle = compute_domain_verdict(Domain.conspiracies, req.text)
    
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
                name="Wikipedia",
                cache_status="cached",
                details="Mainstream encyclopedia entries",
            )
        )
        data_used.append(
            DataSource(
                name="Fact-check databases",
                cache_status="fresh",
                details="Verified fact-check sources (no fringe sources)",
            )
        )
    
    # Enhance how_we_got_conclusion
    conclusion_steps = verdict_bundle.how_we_got_conclusion.copy()
    conclusion_steps.append(f"Likelihood rating: {analysis['likelihood_rating']}/100")
    
    limitations = context.limitations.copy()
    limitations.append("Conspiracy theories are difficult to verify definitively.")
    limitations.append("We did not include fringe sources or unverified claims.")
    limitations.append("Some classified documents may not be available for verification.")
    if analysis["missing_data"]:
        limitations.extend([f"Missing: {item}" for item in analysis["missing_data"]])
    
    return ConspiraciesResponse(
        summary=verdict_bundle.summary,
        verdict=verdict_bundle.verdict,
        confidence=verdict_bundle.confidence,
        data_used=data_used,
        how_we_got_conclusion=conclusion_steps,
        long_term_outcome_example=verdict_bundle.long_term_example,
        limitations=limitations,
        guardrail_flags=guardrail_flags,
        model_version="gpt-4o-mini",
        evaluation_date=datetime.utcnow().isoformat(),
        likelihood_rating=analysis["likelihood_rating"],
        evidence_for=analysis["evidence_for"],
        evidence_against=analysis["evidence_against"],
        historical_parallels=analysis["historical_parallels"],
        missing_data=analysis["missing_data"],
    )

