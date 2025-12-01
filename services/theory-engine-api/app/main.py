"""
Entry point for the dock108 Theory Engine FastAPI service.

This service provides the core API for all dock108 theory evaluation surfaces:
- Sports betting theory evaluation
- Crypto strategy interpretation
- Stock analysis
- Conspiracy theory fact-checking
- Sports highlight playlist generation

All domain-specific logic is delegated to routers, with shared utilities
for database access, logging, and context fetching.
"""

from collections.abc import Callable
from datetime import datetime

from .utils import now_utc

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .logging_config import configure_logging

from py_core import (
    Domain,
    TheoryRequest,
    TheoryResponse,
    DataSource,
    evaluate_guardrails,
    has_hard_block,
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

from .routers import bets, conspiracies, crypto, crypto_data, highlights, playlist, sports_data, stocks, strategy, stocks_strategy

app = FastAPI(title="Dock108 Theory Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_logging()
app.include_router(playlist.router)
app.include_router(bets.router)
app.include_router(crypto.router)
app.include_router(stocks.router)
app.include_router(stocks_strategy.router)
app.include_router(conspiracies.router)
app.include_router(highlights.router)
app.include_router(strategy.router)
app.include_router(sports_data.router)
app.include_router(crypto_data.router)


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
    """
    End-to-end theory evaluation with guardrails and context enrichment.
    
    This is the main entry point for theory evaluation across all domains.
    It:
    1. Routes the request to the appropriate domain
    2. Evaluates guardrails (content filtering, safety checks)
    3. Fetches relevant context (odds, prices, videos, etc.)
    4. Computes domain-specific verdict using LLM
    5. Returns structured response with confidence and limitations
    """

    domain = req.domain or route_domain(req.text)
    guardrail_results = evaluate_guardrails(req.text, domain)
    
    # Check for hard blocks
    if has_hard_block(guardrail_results):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="This theory cannot be evaluated due to guardrail restrictions.",
        )
    
    guardrail_flags = summarize_guardrails(guardrail_results)

    fetcher = DOMAIN_FETCHERS.get(domain)
    context = fetcher(req.text) if fetcher else ContextResult()

    verdict_bundle = compute_domain_verdict(domain, req.text)

    # Build data_used list from context
    data_used: list[DataSource] = []
    if context.data_source_name:
        # Use the data source info from the fetcher
        data_used.append(
            DataSource(
                name=context.data_source_name,
                cache_status=context.cache_status,
                details=context.data_source_details,
            )
        )
    else:
        # Fallback to old sources list
        for source in context.sources:
            cache_status = "cached" if "cache" in source.lower() or "stub" in source.lower() else "fresh"
            data_used.append(
                DataSource(
                    name=source,
                    cache_status=cache_status,
                    details=None,
                )
            )

    # Add default limitations if none provided
    limitations = context.limitations.copy()
    if not limitations:
        limitations.append("This is a pattern check, not a full market model.")
        limitations.append("Analysis based on available data; may not include all relevant factors.")

    return TheoryResponse(
        summary=verdict_bundle.summary,
        verdict=verdict_bundle.verdict,
        confidence=verdict_bundle.confidence,
        data_used=data_used,
        how_we_got_conclusion=verdict_bundle.how_we_got_conclusion,
        long_term_outcome_example=verdict_bundle.long_term_example,
        limitations=limitations,
        guardrail_flags=guardrail_flags,
        model_version="gpt-4o-mini",
        evaluation_date=now_utc().isoformat(),
    )

