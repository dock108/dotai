"""Shared schemas and helpers for dock108 services."""

from __future__ import annotations

from .schemas.theory import Domain, TheoryRequest, TheoryResponse, DataSource
from .schemas.highlight_request import (
    HighlightRequestSpec,
    HighlightRequestParseResult,
    Sport,
    LoopMode,
    ContentMix,
    DateRange,
)
from .guardrails.engine import evaluate_guardrails, has_hard_block, summarize_guardrails
from .guardrails.sports_highlights import (
    check_sports_highlight_guardrails,
    has_hard_block_sports,
    summarize_sports_guardrails,
    normalize_sports_request,
)
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
from .scoring.video import (
    VideoScore,
    calculate_highlight_score,
    calculate_general_video_score,
    get_channel_reputation_score,
)
from .playlist.staleness import (
    compute_stale_after,
    is_stale,
    should_refresh_playlist,
)
from .clients.youtube import YouTubeClient, VideoCandidate

__all__ = [
    "__version__",
    "Domain",
    "TheoryRequest",
    "TheoryResponse",
    "DataSource",
    "HighlightRequestSpec",
    "HighlightRequestParseResult",
    "Sport",
    "LoopMode",
    "ContentMix",
    "DateRange",
    "evaluate_guardrails",
    "has_hard_block",
    "summarize_guardrails",
    "check_sports_highlight_guardrails",
    "has_hard_block_sports",
    "summarize_sports_guardrails",
    "normalize_sports_request",
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
    "compute_stale_after",
    "is_stale",
    "should_refresh_playlist",
    "YouTubeClient",
    "VideoCandidate",
    "VideoScore",
    "calculate_highlight_score",
    "calculate_general_video_score",
    "get_channel_reputation_score",
]

__version__ = "0.1.0"

