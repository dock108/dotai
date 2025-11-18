"""Shared schemas and helpers for dock108 services."""

from __future__ import annotations

from .schemas.theory import Domain, TheoryRequest, TheoryResponse, DataSource
from .guardrails.engine import evaluate_guardrails, has_hard_block, summarize_guardrails
from .domain.router import route_domain
from .data.fetchers import (
    fetch_conspiracy_context,
    fetch_crypto_context,
    fetch_odds_context,
    fetch_stock_context,
    fetch_youtube_context,
    ContextResult,
)
from .data.cache import CacheKey, CacheEntry, ContextCache
from .scoring.metrics import compute_domain_verdict

__all__ = [
    "__version__",
    "Domain",
    "TheoryRequest",
    "TheoryResponse",
    "evaluate_guardrails",
    "summarize_guardrails",
    "route_domain",
    "ContextResult",
    "fetch_youtube_context",
    "fetch_odds_context",
    "fetch_crypto_context",
    "fetch_stock_context",
    "fetch_conspiracy_context",
    "CacheKey",
    "CacheEntry",
    "ContextCache",
    "compute_domain_verdict",
]

__version__ = "0.1.0"

