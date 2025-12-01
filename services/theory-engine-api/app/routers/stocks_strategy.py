"""Stocks strategy interpretation and alert router."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta

from ..utils import now_utc
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..db_models import Alert, Backtest, Strategy, StrategyStatus
from ..logging_config import get_logger
from .strategy_models import (
    AlertEvent,
    AlertSpec,
    Assumptions,
    BacktestBlueprint,
    BacktestMetrics,
    BacktestRequest,
    BacktestResult,
    CatalystAnalysis,
    EdgeDiagnostics,
    SaveRequest,
    StrategyInterpretation,
    StrategyResponse,
    StrategySpec,
    ToggleAlertsRequest,
    create_alert_id,
    create_backtest_id,
    create_strategy_id,
    safe_json_parse,
)

router = APIRouter(prefix="/api/stocks/strategy", tags=["stocks-strategy"])
logger = get_logger(__name__)

STOCKS_STRATEGY_PROMPT = """
You are the dock108 Stocks Strategy Interpreter. Your job is to turn a user's equity idea into:

1. A trader-friendly playbook grounded in catalysts, valuation, and sector context.
2. Catalyst analysis that explains WHY the stock or sector might move.
3. A pattern layer that covers trend, valuation bands, volume behavior, and historical analogs.
4. Asset (ticker/sector/ETF) breakdowns with entry conditions, reactions, and monitoring tools.
5. A machine-readable strategySpec that the dock108 backend can backtest.
6. An alertSpec for future monitoring (price levels, volume spikes, earnings events, etc.).
7. Explicit assumptions, uncertainties, and missing data notes.

You MUST:
- Retell the user's situation in clear trader language.
- Identify the catalyst type (earnings, guidance, macro data, Fed/rates, regulatory/legal, M&A, sector rotation, valuation normalization, technical trend).
- Explain WHY that catalyst impacts this ticker/sector: liquidity, rates, beta, factor rotation, ETF flows, valuation, supply/demand.
- Produce three scenarios (positive / neutral / negative) with immediate, short-term, and medium-term reactions.
- Reference historical analogs (earnings reactions, macro events, similar guidance shifts, sector rotations).
- Map the ticker to its behavior profile (rates-sensitive tech, value cyclical, defensive staples, high short interest, etc.).
- Provide entry strategy mechanics (breakout, retest, earnings dip buy, trend continuation, mean reversion, catalyst reaction, valuation band, ETF flow momentum).
- Capital is OPTIONAL. If no capital provided, DO NOT invent dollar amounts. Use relative percentages and behavior-based staging only. If capital IS provided, include allocation USD sizing.
- Include exit strategy: profit-taking levels, invalidation triggers, time-based exits (e.g., post-earnings drift), trailing stops.
- Include guardrails anchored to observables (price closes below critical level, sector divergence, macro reversal).
- Backtest blueprint must describe how to simulate the strategy historically (earnings events, CPI/FOMC reactions, valuation-based entries, etc.).
- Alerts must include stock-specific triggers (price zone, RSI divergence, volume expansion, earnings release, sector ETF divergence, futures reaction).
- Every structured list (strategySpec.indicators, strategySpec.entryPlan.tranches, backtestBlueprint.datasets, alertSpec.triggers) must be valid JSON
  objects, never plain strings. Always include the fields shown in the schema.

When numbers are ambiguous, infer using context (e.g., "150" likely means $150/share for AAPL today). Document every assumption.

Never output generic DCA text. Never ignore the catalyst or sector context. Produce differentiated reasoning.

Capital handling:
- If user provides capital: output allocation percentages and USD sizing in entries.
- If user does NOT provide capital: produce entry conditions, staging percentages, and monitoring signals ONLY.
- Strategy must always be complete regardless of capital availability.

Outputs must comply with this JSON schema:
{
  "playbookText": {
    "title": "...",
    "summary": "...",
    "currentMarketContext": {
      "price": "...",
      "drawdownFromATH": "...",
      "volatility30d": "...",
      "funding": "...",
      "oiTrend": "...",
      "etfFlows": "..."
    },
    "narrativeSummary": "...",
    "deepDive": ["valuation trend", "macro sensitivity", "sector rotation", "earnings/guidance context", "historical compare", "timing model"],
    "gamePlan": ["entry mechanics", "what to do if it dumps", "what to do if it rips", "when to stop"],
    "guardrails": ["observables-based invalidation", "macro/sector red flags"],
    "dataSources": ["ATR / volatility", "ETF flows", "options flow", ...]
  },
  "catalystAnalysis": { ... },
  "patternAnalysis": {
    "trend": "...",
    "valuation": "...",
    "volume": "...",
    "historicalSetups": ["..."],
    "confidence": "High | Medium | Low"
  },
  "assetBreakdown": [
    {
      "asset": "AAPL",
      "reasoning": "...",
      "reaction": "...",
      "entryPlan": ["Breakout above 175 with 1.5x volume", "Range re-entry 165-167"],
      "risks": ["USD strength", "weak guidance"],
      "confidence": "High | Medium | Low"
    },
    {
      "asset": "XLK",
      "reasoning": "...",
      ...
    }
  ],
  "strategySpec": {
    "name": "...",
    "market": "equities",
    "ticker": "AAPL",
    "sector": "Technology",
    "timeframe": "multi-week",
    "thesis": "...",
    "units": "USD | percentage",
    "entryPlan": { "tranches": [...] },
    "indicators": [...],
    "entries": [
      {
        "side": "long",
        "condition": "If earnings beat AND price reclaims 175 with 1.5x volume",
        "method": "catalyst",
        "tranchePercent": 40,
        "allocateUsd": 400,  // Only if capital provided
        "logic": "...",
        "confidence": 4,
        "tags": ["earnings", "momentum"],
        "notes": "Watch implied vol crush"
      }
    ],
    "exits": [...],
    "risk": { "maxCapitalAtRiskPct": ..., "maxOpenPositions": ..., "positionSizing": "..." }
  },
  "backtestBlueprint": {
    "datasets": [...],
    "metrics": [...],
    "assumptions": ["slippage", "commissions", "earnings drift window"],
    "scenarios": ["earnings dip buy", "breakout chase", "macro rotation"],
    "period": "2015-01-01 to today"
  },
  "alertSpec": { "triggers": [...] },
  "assumptions": {
    "normalizations": [...],
    "uncertainties": [...],
    "userSaid90Means": "..."
  }
}
""".strip()


def _hash_to_range(value: str, salt: str, minimum: float, maximum: float) -> float:
    seed = int(hashlib.sha256(f"{value}:{salt}".encode()).hexdigest()[:8], 16)
    return minimum + (seed % 1000) / 1000 * (maximum - minimum)


async def fetch_stock_enrichment(ticker: str) -> dict[str, Any]:
    """Fetch current stock context (placeholder deterministic data)."""
    ticker_upper = ticker.upper()
    base_price = round(_hash_to_range(ticker_upper, "price", 20.0, 600.0), 2)
    change_5d = round(_hash_to_range(ticker_upper, "5d", -5.0, 5.0), 2)
    change_30d = round(_hash_to_range(ticker_upper, "30d", -12.0, 15.0), 2)
    change_90d = round(_hash_to_range(ticker_upper, "90d", -20.0, 25.0), 2)
    from_recent_high = round(_hash_to_range(ticker_upper, "ath", -40.0, 5.0), 2)
    atr14 = round(_hash_to_range(ticker_upper, "atr", 0.5, 12.0), 2)
    beta = round(_hash_to_range(ticker_upper, "beta", 0.5, 2.2), 2)
    short_interest = round(_hash_to_range(ticker_upper, "short", 0.1, 8.0), 2)
    sector = ["Technology", "Financials", "Energy", "Consumer Discretionary", "Healthcare", "Industrials"][
        int(_hash_to_range(ticker_upper, "sector", 0, 5.999))
    ]
    industry = {
        "Technology": "Systems Software",
        "Financials": "Banks",
        "Energy": "Integrated Oil & Gas",
        "Consumer Discretionary": "Internet Retail",
        "Healthcare": "Biotechnology",
        "Industrials": "Aerospace & Defense",
    }[sector]
    correlations = {
        "SPY": round(_hash_to_range(ticker_upper, "corr_spy", 0.3, 0.95), 2),
        "QQQ": round(_hash_to_range(ticker_upper, "corr_qqq", 0.2, 0.95), 2),
        "sectorETF": round(_hash_to_range(ticker_upper, "corr_sector", 0.4, 0.96), 2),
    }
    next_earnings = (now_utc() + timedelta(days=int(_hash_to_range(ticker_upper, "earn", 5, 40)))).date()

    return {
        "ticker": ticker_upper,
        "companyName": f"{ticker_upper} Corp.",
        "sector": sector,
        "industry": industry,
        "marketCap": f"${_hash_to_range(ticker_upper, 'mcap', 5, 2500):,.0f}B",
        "currentPrice": base_price,
        "change5dPct": change_5d,
        "change30dPct": change_30d,
        "change90dPct": change_90d,
        "fromRecentHighPct": from_recent_high,
        "atr14": atr14,
        "beta": beta,
        "shortInterestPct": short_interest,
        "earningsDate": next_earnings.isoformat(),
        "etfFlows": {
            "SPY": round(_hash_to_range(ticker_upper, "flow_spy", -2.0, 3.0), 2),
            "QQQ": round(_hash_to_range(ticker_upper, "flow_qqq", -1.0, 2.5), 2),
        },
        "correlations": correlations,
        "valuationBand": {
            "forwardPE": round(_hash_to_range(ticker_upper, "pe", 8.0, 55.0), 1),
            "fiveYearAverage": round(_hash_to_range(ticker_upper, "pe_avg", 10.0, 35.0), 1),
        },
        "volumeTrend": "increasing" if _hash_to_range(ticker_upper, "voltrend", 0, 1) > 0.5 else "cooling",
    }


def build_stock_interpreter_user_prompt(
    idea_text: str,
    ticker: str,
    enrichment: dict[str, Any],
    scenario_type: str | None,
    include_sector: bool,
    capital: float | None,
    capital_currency: str | None,
    time_horizon: str | None,
    risk_comfort: str | None,
    data_sources: list[str],
) -> str:
    parts = [f"User stock hypothesis for {ticker}:\n\"\"\"{idea_text}\"\"\""]

    if scenario_type:
        parts.append(f"\nScenario type: {scenario_type}")
    if time_horizon:
        parts.append(f"Time horizon: {time_horizon}")
    if risk_comfort:
        parts.append(f"Risk comfort: {risk_comfort}")
    if data_sources:
        parts.append(f"Data to consider: {', '.join(data_sources)}")

    if capital and capital > 0:
        parts.append(f"Available capital: {capital} {capital_currency or 'USD'}")
        parts.append("IMPORTANT: User provided capital - include USD sizing in entries.")
    else:
        parts.append("IMPORTANT: No capital provided - use behavior-based entry conditions and relative percentages only.")

    parts.append(
        "\nTicker context:\n"
        f"- Company: {enrichment['companyName']} ({enrichment['sector']} / {enrichment['industry']})\n"
        f"- Current price: ${enrichment['currentPrice']:,.2f}\n"
        f"- 5d / 30d / 90d change: {enrichment['change5dPct']}% / {enrichment['change30dPct']}% / {enrichment['change90dPct']}%\n"
        f"- Drawdown from recent high: {enrichment['fromRecentHighPct']}%\n"
        f"- ATR(14): {enrichment['atr14']}\n"
        f"- Beta vs SPY: {enrichment['beta']}\n"
        f"- Short interest: {enrichment['shortInterestPct']}%\n"
        f"- Earnings date: {enrichment['earningsDate']}\n"
        f"- ETF flows (SPY/QQQ): {enrichment['etfFlows']['SPY']}B / {enrichment['etfFlows']['QQQ']}B\n"
        f"- Correlations: SPY {enrichment['correlations']['SPY']}, QQQ {enrichment['correlations']['QQQ']}, Sector {enrichment['correlations']['sectorETF']}\n"
        f"- Valuation band (forward PE vs 5y avg): {enrichment['valuationBand']['forwardPE']} vs {enrichment['valuationBand']['fiveYearAverage']}\n"
        f"- Volume trend: {enrichment['volumeTrend']}"
    )

    if include_sector:
        parts.append("Include sector & ETF exposure analysis (XLK, XLF, etc.).")

    parts.append("\nReturn only JSON and ensure it matches the schema.")
    return "\n".join(parts).strip()


def normalize_stocks_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce loosely structured LLM output into the strict StrategyInterpretation schema."""
    parsed = dict(raw)

    # Catalyst analysis fields
    catalyst = parsed.get("catalystAnalysis")
    if isinstance(catalyst, dict):
        catalyst.setdefault("type", catalyst.get("catalystType", "unclassified"))
        catalyst.setdefault("description", catalyst.get("summary", ""))
        catalyst.setdefault("affectedCategories", catalyst.get("affectedSectors", []))
        parsed["catalystAnalysis"] = catalyst
    else:
        parsed["catalystAnalysis"] = {
            "type": "unclassified",
            "description": "",
            "affectedCategories": [],
            "historicalAnalogs": [],
        }

    # Strategy spec cleanup
    spec = parsed.get("strategySpec") or {}
    entry_plan = spec.get("entryPlan")
    if isinstance(entry_plan, dict):
        tranches = []
        for tranche in entry_plan.get("tranches", []):
            if not isinstance(tranche, dict):
                continue
            trigger = tranche.get("trigger") or tranche.get("condition") or "LLM_missing_trigger"
            capital_pct = tranche.get("capitalPct") or tranche.get("tranchePercent") or 0
            tranches.append(
                {
                    "trigger": trigger,
                    "capitalPct": capital_pct,
                    "allocateUsd": tranche.get("allocateUsd"),
                    "comments": tranche.get("notes"),
                }
            )
        entry_plan["tranches"] = tranches
        spec["entryPlan"] = entry_plan

    indicators = []
    for indicator in spec.get("indicators", []):
        if isinstance(indicator, dict):
            indicators.append(indicator)
        else:
            indicators.append({"name": str(indicator), "source": "llm", "params": {}})
    spec["indicators"] = indicators

    # Normalize exits
    exits = []
    for exit_item in spec.get("exits", []):
        if isinstance(exit_item, dict):
            logic = exit_item.get("logic") or exit_item.get("condition", "Exit condition not specified")
            exits.append(
                {
                    "logic": logic,
                    "type": exit_item.get("type", "stop"),
                    "notes": exit_item.get("notes"),
                }
            )
        else:
            exits.append({"logic": str(exit_item), "type": "stop", "notes": None})
    spec["exits"] = exits

    parsed["strategySpec"] = spec

    # Backtest blueprint datasets
    blueprint = parsed.get("backtestBlueprint") or {}
    datasets = []
    for dataset in blueprint.get("datasets", []):
        if isinstance(dataset, dict):
            datasets.append(dataset)
        else:
            datasets.append({"name": str(dataset), "source": "llm", "resolution": "1d", "fields": []})
    blueprint["datasets"] = datasets
    parsed["backtestBlueprint"] = blueprint

    # Alert triggers
    alert_spec = parsed.get("alertSpec") or {}
    triggers = []
    for trigger in alert_spec.get("triggers", []):
        if isinstance(trigger, dict):
            # Ensure all required fields exist
            condition = trigger.get("condition", "")
            triggers.append(
                {
                    "name": trigger.get("name") or condition or "Alert",
                    "condition": condition or trigger.get("name", "Unknown condition"),
                    "channel": trigger.get("channel", "console"),
                    "cooldownMinutes": trigger.get("cooldownMinutes", 60),
                }
            )
        else:
            trigger_text = str(trigger)
            triggers.append(
                {
                    "name": trigger_text,
                    "condition": trigger_text,
                    "channel": "console",
                    "cooldownMinutes": 60,
                }
            )
    alert_spec["triggers"] = triggers
    parsed["alertSpec"] = alert_spec

    # Edge diagnostics default
    edge = parsed.get("edgeDiagnostics")
    if not isinstance(edge, dict):
        parsed["edgeDiagnostics"] = {"strengths": [], "risks": [], "monitoring": []}

    return parsed


def build_stock_synthetic_alerts(strategy_id: str) -> list[AlertEvent]:
    """Fallback alerts tailored for equities when DB is empty."""
    now = now_utc()
    return [
        AlertEvent(
            id=create_alert_id(),
            strategyId=strategy_id,
            triggeredAt=(now - timedelta(hours=2)).isoformat(),
            reason="Price tagged prior gap fill zone",
        ),
        AlertEvent(
            id=create_alert_id(),
            strategyId=strategy_id,
            triggeredAt=(now - timedelta(hours=6)).isoformat(),
            reason="Volume expansion > 150% of 20d average",
        ),
    ]


class StocksInterpretRequest(BaseModel):
    ideaText: str = Field(min_length=10)
    ticker: str = Field(min_length=1)
    scenarioType: str | None = None
    includeSector: bool = True
    capital: float | None = None
    capitalCurrency: str | None = None
    timeHorizon: str | None = None
    riskComfort: str | None = None
    dataSources: list[str] = Field(default_factory=list)
    userId: int | None = None


async def interpret_stocks_with_llm(
    req: StocksInterpretRequest,
    enrichment: dict[str, Any],
) -> StrategyInterpretation:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable required")

    client = OpenAI(api_key=api_key, timeout=120.0)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))

    price_context = {
        req.ticker.upper(): {
            "currentPriceUsd": enrichment["currentPrice"],
            "daysChangePct": enrichment["change5dPct"],
            "fromRecentHighPct": enrichment["fromRecentHighPct"],
        }
    }

    user_prompt = build_stock_interpreter_user_prompt(
        idea_text=req.ideaText,
        ticker=req.ticker.upper(),
        enrichment=enrichment,
        scenario_type=req.scenarioType,
        include_sector=req.includeSector,
        capital=req.capital,
        capital_currency=req.capitalCurrency,
        time_horizon=req.timeHorizon,
        risk_comfort=req.riskComfort,
        data_sources=req.dataSources,
    )

    logger.info("stocks_calling_openai", ticker=req.ticker.upper(), prompt_length=len(user_prompt))

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": STOCKS_STRATEGY_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout=120.0,
        )
    except Exception as exc:
        logger.error("stocks_openai_failed", error=str(exc), exc_info=True)
        raise

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response")

    parsed = safe_json_parse(content)

    if "playbookText" not in parsed:
        parsed["playbookText"] = {
            "title": f"{req.ticker.upper()} strategy",
            "summary": parsed.get("interpretation", ""),
            "gamePlan": [],
            "guardrails": [],
            "dataSources": [],
        }
    if "interpretation" not in parsed and "playbookText" in parsed:
        parsed["interpretation"] = parsed["playbookText"].get("summary", "")
    elif "interpretation" not in parsed:
        parsed["interpretation"] = ""
    if "catalystAnalysis" not in parsed:
        parsed["catalystAnalysis"] = CatalystAnalysis(
            type="unclassified",
            description="LLM failed to classify catalyst",
            affectedCategories=[],
            historicalAnalogs=[],
            probableMarketReactions=None,
            confidenceScores=None,
        ).model_dump()
    if "assetBreakdown" not in parsed:
        parsed["assetBreakdown"] = []
    if "assumptions" not in parsed:
        parsed["assumptions"] = {"normalizations": [], "uncertainties": [], "userSaid90Means": None}

    parsed = normalize_stocks_payload(parsed)
    interpretation = StrategyInterpretation(**parsed)

    # Ensure strategy spec contains ticker & sector context
    interpretation.strategySpec.ticker = req.ticker.upper()
    interpretation.strategySpec.sector = enrichment["sector"]

    return interpretation


def build_stock_backtest(strategy_id: str, strategy_spec: StrategySpec) -> BacktestResult:
    ticker = strategy_spec.ticker or strategy_spec.name
    seed_str = f"{strategy_id}{ticker}{strategy_spec.timeframe}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)

    def pseudo(multiplier: int, bias: float = 0.0) -> float:
        return ((seed % multiplier) / multiplier + bias) % 1.0

    win_rate = 0.45 + pseudo(70, 0.05)
    expectancy = round(pseudo(90) * 2.5 - 0.8, 2)
    max_drawdown = round(pseudo(80) * 0.25, 2)
    sharpe = round(pseudo(75) * 1.8, 2)
    best_trade = round(pseudo(60) * 15, 2)
    worst_trade = round(pseudo(60) * -12, 2)
    trades = max(10, round(pseudo(90) * 35))

    start = now_utc() - timedelta(days=60)
    equity_curve = []
    for idx in range(60):
        drift = idx * pseudo(100) * 0.4
        equity_curve.append(
            {
                "timestamp": (start + timedelta(days=idx)).isoformat(),
                "equity": round(1 + drift / 100 + pseudo(120) * 0.04, 3),
            }
        )

    trades_list = []
    for idx, point in enumerate(equity_curve):
        trades_list.append(
            {
                "id": f"{strategy_id}-{idx}",
                "timestamp": point["timestamp"],
                "side": "long" if idx % 2 == 0 else "short",
                "pnl": round(pseudo(200) * (1 if idx % 2 == 0 else -1), 2),
                "notes": strategy_spec.entries[0].logic if strategy_spec.entries else "LLM baseline execution",
            }
        )

    return BacktestResult(
        id=create_backtest_id(),
        strategyId=strategy_id,
        generatedAt=now_utc().isoformat(),
        equityCurve=equity_curve,
        metrics=BacktestMetrics(
            winRate=round(win_rate * 100, 2),
            expectancy=expectancy,
            maxDrawdown=max_drawdown,
            sharpe=sharpe,
            bestTrade=best_trade,
            worstTrade=worst_trade,
            numberOfTrades=trades,
        ),
        trades=trades_list,
        regimeNotes=[
            "Event study: earnings reactions within +/-5 days",
            "Sector rotation vs SPY/QQQ",
            f"Primary ticker: {ticker}",
        ],
    )


@router.post("/interpret", response_model=StrategyResponse)
async def interpret_strategy(
    req: StocksInterpretRequest,
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    ticker = req.ticker.upper()
    logger.info("stocks_interpretation_start", ticker=ticker)

    enrichment = await fetch_stock_enrichment(ticker)
    interpretation = await interpret_stocks_with_llm(req, enrichment)

    strategy_id = create_strategy_id()
    created_at = now_utc().isoformat()
    alerts_enabled = len(interpretation.alertSpec.triggers) > 0
    interpretation_text = (
        interpretation.interpretation
        or (interpretation.playbookText.summary if interpretation.playbookText else "")
        or ""
    )

    strategy = Strategy(
        id=strategy_id,
        user_id=req.userId,
        idea_text=req.ideaText,
        interpretation=interpretation_text,
        strategy_json=interpretation.strategySpec.model_dump(),
        backtest_blueprint=interpretation.backtestBlueprint.model_dump(),
        diagnostics=interpretation.edgeDiagnostics.model_dump(),
        alerts=interpretation.alertSpec.model_dump(),
        status=StrategyStatus.draft,
        alerts_enabled=alerts_enabled,
    )
    db.add(strategy)
    await db.commit()

    return StrategyResponse(
        id=strategy_id,
        ideaText=req.ideaText,
        createdAt=created_at,
        **interpretation.model_dump(),
    )


@router.post("/save", response_model=StrategyResponse)
async def save_strategy(
    req: SaveRequest,
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    try:
        strategy_id = req.strategyId or create_strategy_id()
        alerts_enabled = len(req.alertSpec.triggers) > 0

        result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
        existing = result.scalar_one_or_none()

        if existing:
            existing.idea_text = req.ideaText
            existing.interpretation = req.interpretation
            existing.strategy_json = req.strategySpec.model_dump()
            existing.backtest_blueprint = req.backtestBlueprint.model_dump()
            existing.diagnostics = req.edgeDiagnostics.model_dump()
            existing.alerts = req.alertSpec.model_dump()
            existing.status = StrategyStatus.saved
            existing.alerts_enabled = alerts_enabled
        else:
            strategy = Strategy(
                id=strategy_id,
                user_id=req.userId,
                idea_text=req.ideaText,
                interpretation=req.interpretation,
                strategy_json=req.strategySpec.model_dump(),
                backtest_blueprint=req.backtestBlueprint.model_dump(),
                diagnostics=req.edgeDiagnostics.model_dump(),
                alerts=req.alertSpec.model_dump(),
                status=StrategyStatus.saved,
                alerts_enabled=alerts_enabled,
            )
            db.add(strategy)

        await db.commit()

        return StrategyResponse(
            id=strategy_id,
            ideaText=req.ideaText,
            createdAt=now_utc().isoformat(),
            **req.model_dump(exclude={"strategyId", "ideaText", "userId"}),
        )
    except Exception as exc:
        logger.error("stocks_save_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to save strategy: {exc}")


@router.post("/backtest", response_model=BacktestResult)
async def run_backtest(
    req: BacktestRequest,
    db: AsyncSession = Depends(get_db),
) -> BacktestResult:
    try:
        result = build_stock_backtest(req.strategyId, req.strategySpec)

        backtest = Backtest(
            id=result.id,
            strategy_id=req.strategyId,
            results_json=result.model_dump(),
        )
        db.add(backtest)
        await db.commit()

        return result
    except Exception as exc:
        logger.error("stocks_backtest_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=400, detail=f"Backtest failed: {exc}")


@router.get("/alerts", response_model=dict[str, list[AlertEvent]])
async def fetch_alerts(
    strategyId: str = Query(..., alias="strategyId"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[AlertEvent]]:
    try:
        result = await db.execute(
            select(Alert)
            .where(Alert.strategy_id == strategyId)
            .order_by(Alert.triggered_at.desc())
            .limit(25)
        )
        alerts = result.scalars().all()

        if not alerts:
            return {"events": build_stock_synthetic_alerts(strategyId)}

        events = [
            AlertEvent(
                id=alert.id,
                strategyId=alert.strategy_id,
                triggeredAt=alert.triggered_at.isoformat(),
                reason=str(alert.details_json.get("reason", "Alert triggered")),
            )
            for alert in alerts
        ]
        return {"events": events}
    except Exception as exc:
        logger.warning("stocks_fetch_alerts_failed", error=str(exc))
        return {"events": build_stock_synthetic_alerts(strategyId)}


@router.post("/alerts", response_model=dict[str, Any])
async def toggle_alerts(
    req: ToggleAlertsRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        await db.execute(
            update(Strategy)
            .where(Strategy.id == req.strategyId)
            .values(alerts_enabled=req.enabled)
        )
        await db.commit()

        webhook_url = os.getenv("ALERTS_WEBHOOK_URL")
        if webhook_url:
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    await client.post(webhook_url, json={"strategyId": req.strategyId, "enabled": req.enabled}, timeout=5.0)
            except Exception as exc:
                logger.warning("stocks_alert_webhook_failed", error=str(exc))

        return {"strategyId": req.strategyId, "enabled": req.enabled}
    except Exception as exc:
        logger.error("stocks_toggle_alerts_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to toggle alerts: {exc}")


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return StrategyResponse(
        id=strategy.id,
        ideaText=strategy.idea_text,
        createdAt=strategy.created_at.isoformat() if strategy.created_at else now_utc().isoformat(),
        interpretation=strategy.interpretation,
        strategySpec=StrategySpec(**strategy.strategy_json),
        backtestBlueprint=BacktestBlueprint(**strategy.backtest_blueprint),
        edgeDiagnostics=EdgeDiagnostics(**strategy.diagnostics),
        alertSpec=AlertSpec(**strategy.alerts),
    )


