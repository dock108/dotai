"""Entry point for the dock108 Theory Engine FastAPI service."""

from collections.abc import Callable

from fastapi import FastAPI

from py_core import (
    Domain,
    TheoryRequest,
    TheoryResponse,
    evaluate_guardrails,
    summarize_guardrails,
    route_domain,
    fetch_youtube_context,
    fetch_odds_context,
    fetch_crypto_context,
    fetch_stock_context,
    fetch_conspiracy_context,
    compute_domain_verdict,
    ContextResult,
)

app = FastAPI(title="Dock108 Theory Engine", version="0.1.0")


@app.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Simple readiness probe used by infra and CI."""
    return {"status": "ok"}


ContextFetcher = Callable[[str], ContextResult]

DOMAIN_FETCHERS: dict[Domain, ContextFetcher] = {
    Domain.bets: lambda text: fetch_odds_context(text, limit=5),
    Domain.crypto: lambda text: fetch_crypto_context(text, limit=5),
    Domain.stocks: lambda text: fetch_stock_context(text, limit=5),
    Domain.conspiracies: lambda text: fetch_conspiracy_context(text, limit=3),
    Domain.playlist: lambda text: fetch_youtube_context(text, limit=8),
}


@app.post("/api/theory/evaluate", response_model=TheoryResponse, tags=["theory"])
async def evaluate_theory(req: TheoryRequest) -> TheoryResponse:
    """End-to-end theory evaluation stub."""

    domain = req.domain or route_domain(req.text)
    guardrail_results = evaluate_guardrails(req.text, domain)
    guardrail_flags = summarize_guardrails(guardrail_results)

    fetcher = DOMAIN_FETCHERS.get(domain)
    context = fetcher(req.text) if fetcher else ContextResult()

    verdict_bundle = compute_domain_verdict(domain, req.text)
    combined_reasoning = "\n\n".join(
        [verdict_bundle.reasoning, *context.highlights] if context.highlights else [verdict_bundle.reasoning]
    )

    return TheoryResponse(
        verdict=verdict_bundle.verdict,
        confidence=verdict_bundle.confidence,
        reasoning=combined_reasoning,
        data_sources=context.sources,
        limitations=context.limitations,
        long_term_outcome_example=verdict_bundle.long_term_example,
        guardrail_flags=guardrail_flags,
    )

