"""Shared strategy models and helpers for strategy interpreters."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class StrategyIndicator(BaseModel):
    name: str
    source: str
    params: dict[str, Any] = Field(default_factory=dict)


class StrategyEntry(BaseModel):
    side: str  # "long" | "short"
    condition: str | None = None  # Entry condition (e.g., "If ruling is positive AND BTC breaks above 94,500")
    method: str | None = None  # "breakout" | "mean-reversion" | "catalyst" | "trend" | "sentiment"
    tranchePercent: float | None = None  # Percentage allocation if capital provided
    allocateUsd: float | None = None  # USD amount (only if capital provided)
    logic: str
    confidence: int = Field(default=3, ge=0, le=5)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class StrategyExit(BaseModel):
    logic: str
    type: str = "stop"  # "stop" | "target" | "timed" | "conditional"
    notes: str | None = None


class StrategyRisk(BaseModel):
    maxCapitalAtRiskPct: float = Field(ge=0, le=100)
    maxOpenPositions: int = Field(ge=1)
    positionSizing: str


class EntryTranche(BaseModel):
    trigger: str
    capitalPct: float = Field(ge=0, le=100)
    allocateUsd: float | None = None
    comments: str | None = None


class EntryPlan(BaseModel):
    tranches: list[EntryTranche] = Field(default_factory=list)
    maxDeploymentPct: float = Field(default=100.0, ge=0, le=100)


class StrategySpec(BaseModel):
    name: str
    market: str
    timeframe: str
    thesis: str
    ticker: str | None = None
    sector: str | None = None
    units: str | None = None  # "USD" | "thousands" | "percentage"
    entryPlan: EntryPlan | None = None
    indicators: list[StrategyIndicator] = Field(default_factory=list)
    entries: list[StrategyEntry] = Field(default_factory=list)
    exits: list[StrategyExit] = Field(default_factory=list)
    risk: StrategyRisk


class DatasetSpec(BaseModel):
    name: str
    source: str
    resolution: str
    fields: list[str] = Field(default_factory=list)


class BacktestBlueprint(BaseModel):
    datasets: list[DatasetSpec] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)  # ["lump sum", "3-tranche DCA", etc.]
    period: str | None = None  # "2017-01-01 to today"


class BacktestMetrics(BaseModel):
    winRate: float
    expectancy: float
    maxDrawdown: float
    sharpe: float
    bestTrade: float
    worstTrade: float
    numberOfTrades: int


class BacktestResult(BaseModel):
    id: str
    strategyId: str
    equityCurve: list[dict[str, Any]]
    metrics: BacktestMetrics
    trades: list[dict[str, Any]]
    regimeNotes: list[str]
    generatedAt: str


class EdgeDiagnostics(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    monitoring: list[str] = Field(default_factory=list)


class AlertTrigger(BaseModel):
    name: str
    condition: str
    channel: str
    cooldownMinutes: int = Field(ge=0)


class AlertSpec(BaseModel):
    triggers: list[AlertTrigger] = Field(default_factory=list)


class ToggleAlertsRequest(BaseModel):
    strategyId: str
    enabled: bool


class CurrentMarketContext(BaseModel):
    price: str | dict[str, float] | None = None
    drawdownFromATH: str | dict[str, float] | None = None
    volatility30d: str | dict[str, float] | None = None
    funding: str | dict[str, float] | None = None
    oiTrend: str | dict[str, float] | None = None
    etfFlows: str | dict[str, float] | None = None

    @model_validator(mode="after")
    def convert_dicts_to_strings(self) -> "CurrentMarketContext":
        """Convert dict values to formatted strings so frontend can render uniformly."""
        if isinstance(self.price, dict):
            self.price = ", ".join([f"{k}: ${v:,.0f}" for k, v in self.price.items()])
        if isinstance(self.drawdownFromATH, dict):
            self.drawdownFromATH = ", ".join([f"{k}: {v:+.1f}%" for k, v in self.drawdownFromATH.items()])
        if isinstance(self.volatility30d, dict):
            self.volatility30d = ", ".join([f"{k}: {v}" for k, v in self.volatility30d.items()])
        if isinstance(self.funding, dict):
            self.funding = ", ".join([f"{k}: {v}" for k, v in self.funding.items()])
        if isinstance(self.oiTrend, dict):
            self.oiTrend = ", ".join([f"{k}: {v}" for k, v in self.oiTrend.items()])
        if isinstance(self.etfFlows, dict):
            self.etfFlows = ", ".join([f"{k}: {v}" for k, v in self.etfFlows.items()])
        return self


class PlaybookText(BaseModel):
    title: str
    summary: str
    currentMarketContext: CurrentMarketContext | None = None
    narrativeSummary: str | None = None
    deepDive: list[str] = Field(default_factory=list)
    gamePlan: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    dataSources: list[str] = Field(default_factory=list)


class HistoricalAnalog(BaseModel):
    event: str
    cryptoReaction: str
    coinsReactedMost: list[str] = Field(default_factory=list)
    coinsReactedLeast: list[str] = Field(default_factory=list)
    liquiditySimilar: str | None = None
    confidence: str  # "High" | "Medium" | "Low"


class ProbableMarketReactions(BaseModel):
    ifCatalystPositive: str
    ifCatalystNegative: str
    ifCatalystNeutral: str


class ConfidenceScores(BaseModel):
    overall: str  # "High" | "Medium" | "Low"
    assetMapping: str
    timing: str
    magnitude: str


class CatalystAnalysis(BaseModel):
    type: str
    description: str
    affectedCategories: list[str] = Field(default_factory=list)
    historicalAnalogs: list[HistoricalAnalog] = Field(default_factory=list)
    probableMarketReactions: ProbableMarketReactions | None = None
    confidenceScores: ConfidenceScores | None = None


class AssetBreakdownItem(BaseModel):
    asset: str
    reasoning: str
    reaction: str
    entryPlan: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: str  # "High" | "Medium" | "Low"


class PatternAnalysis(BaseModel):
    trend: str | None = None
    valuation: str | None = None
    volume: str | None = None
    historicalSetups: list[str] = Field(default_factory=list)
    confidence: str | None = None


class Assumptions(BaseModel):
    normalizations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    userSaid90Means: str | None = None


class AlertEvent(BaseModel):
    id: str
    strategyId: str
    triggeredAt: str
    reason: str


class StrategyInterpretation(BaseModel):
    interpretation: str | None = None
    playbookText: PlaybookText | None = None
    catalystAnalysis: CatalystAnalysis | None = None
    assetBreakdown: list[AssetBreakdownItem] = Field(default_factory=list)
    patternAnalysis: PatternAnalysis | None = None
    strategySpec: StrategySpec
    backtestBlueprint: BacktestBlueprint
    edgeDiagnostics: EdgeDiagnostics
    alertSpec: AlertSpec
    assumptions: Assumptions | None = None


class StrategyResponse(StrategyInterpretation):
    id: str
    ideaText: str
    createdAt: str


class SaveRequest(StrategyInterpretation):
    strategyId: str | None = None
    ideaText: str = Field(min_length=5)
    userId: int | None = None


class BacktestRequest(BaseModel):
    strategyId: str
    strategySpec: StrategySpec


def create_strategy_id() -> str:
    return f"stg_{uuid4().hex[:12]}"


def create_backtest_id() -> str:
    return f"bt_{uuid4().hex[:12]}"


def create_alert_id() -> str:
    return f"alert_{uuid4().hex[:12]}"


def safe_json_parse(blob: str) -> dict[str, Any]:
    """Parse JSON, handling code blocks if present."""
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", blob)
        if not match:
            raise ValueError("LLM response was not valid JSON")
        return json.loads(match.group(0))


def build_synthetic_alerts(strategy_id: str) -> list[AlertEvent]:
    """Generate synthetic alert events for testing."""
    now = datetime.utcnow()
    return [
        AlertEvent(
            id=create_alert_id(),
            strategyId=strategy_id,
            triggeredAt=(now - timedelta(hours=1)).isoformat(),
            reason="Funding flipped negative on BTC perpetuals",
        ),
        AlertEvent(
            id=create_alert_id(),
            strategyId=strategy_id,
            triggeredAt=(now - timedelta(hours=5)).isoformat(),
            reason="OI jumped 15% intraday on SOL",
        ),
    ]


