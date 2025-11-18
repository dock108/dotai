"""Canonical request/response schemas shared across dock108 services."""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, NonNegativeFloat


class Domain(str, Enum):
    """Supported theory surfaces."""

    bets = "bets"
    crypto = "crypto"
    stocks = "stocks"
    conspiracies = "conspiracies"
    playlist = "playlist"


class TheoryRequest(BaseModel):
    """Unified request payload sent by clients."""

    text: Annotated[str, Field(min_length=10, description="Raw user theory or hypothesis.")]
    domain: Domain | None = Field(
        default=None,
        description="Optional explicit domain. If missing, route_domain() will infer it.",
    )
    user_tier: str | None = Field(
        default=None, description="free/silver/gold/unlimited tier hints for guardrails."
    )


class TheoryResponse(BaseModel):
    """Shared response structure consumed by every frontend."""

    verdict: Annotated[str, Field(description="Short summary verdict (buy/avoid/etc.).")]
    confidence: Annotated[
        NonNegativeFloat, Field(le=1.0, description="0-1 calibrated confidence score.")
    ]
    reasoning: Annotated[str, Field(description="Why the verdict was reached.")]
    data_sources: list[HttpUrl | str] = Field(
        default_factory=list, description="External sources referenced while evaluating."
    )
    limitations: list[str] = Field(
        default_factory=list, description="Caveats about the evaluation."
    )
    long_term_outcome_example: Annotated[
        str, Field(description='Narrative like "If you put $100/mo into this..."')
    ]
    guardrail_flags: list[str] = Field(
        default_factory=list, description="Triggered guardrail identifiers."
    )

