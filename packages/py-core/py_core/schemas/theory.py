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


class DataSource(BaseModel):
    """Data source with cache status."""

    name: str = Field(description="Human-readable name of the data source")
    cache_status: str = Field(description="'cached' or 'fresh'")
    details: str | None = Field(default=None, description="Additional details like date range, query, etc.")


class TheoryResponse(BaseModel):
    """Shared response structure consumed by every frontend - brutally honest format."""

    # 1. Summary
    summary: Annotated[
        str, Field(description="Your theory rewritten cleanly in one sentence.")
    ]

    # 2. Verdict + Confidence
    verdict: Annotated[str, Field(description="Short phrase verdict (e.g., 'Plausible but weak', 'Mostly noise').")]
    confidence: Annotated[
        NonNegativeFloat, Field(le=1.0, description="0-1 calibrated confidence score.")
    ]

    # 3. Data we used
    data_used: list[DataSource] = Field(
        default_factory=list, description="List of data sources with cache status."
    )

    # 4. How we got the conclusion
    how_we_got_conclusion: list[str] = Field(
        default_factory=list,
        description="Step-by-step bullet points explaining the analysis process.",
    )

    # 5. Long-term $100 example
    long_term_outcome_example: Annotated[
        str,
        Field(
            description='Simulation-style line: "If you put $100 into this each time... break even X%, lose Y%, upside Z, downside W."'
        ),
    ]

    # 6. Limits / missing data
    limitations: list[str] = Field(
        default_factory=list,
        description="Brutal honesty: what we didn't include and why (cost, data, MVP scope).",
    )

    # 7. Meta
    guardrail_flags: list[str] = Field(
        default_factory=list, description="Triggered guardrail identifiers."
    )
    model_version: str | None = Field(
        default=None, description="Model/API version used for evaluation."
    )
    evaluation_date: str | None = Field(
        default=None, description="ISO date string of when evaluation was performed."
    )

