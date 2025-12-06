from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseResult(BaseModel):
    event_id: str
    market: str
    stake: float | None = None
    odds: float | None = None
    implied_prob: float | None = None
    ev: float | None = None
    features: Dict[str, Any] = Field(default_factory=dict)


class BacktestResult(BaseResult):
    outcome: str | None = None  # win/loss/push/void
    pnl: float | None = None
    settled_at: str | None = None


class LiveSignal(BaseResult):
    triggered_at: str | None = None
    expires_at: str | None = None
    confidence: float | None = None


class TrendingIndicator(BaseResult):
    window: str | None = None
    trend: str | None = None  # up/down/flat
    score: float | None = None


