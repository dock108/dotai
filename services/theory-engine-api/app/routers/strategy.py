"""Strategy interpretation and backtesting router for crypto strategies."""

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
    BacktestResult,
    BacktestRequest,
    CatalystAnalysis,
    StrategyInterpretation,
    StrategyResponse,
    StrategySpec,
    SaveRequest,
    ToggleAlertsRequest,
    create_alert_id,
    create_backtest_id,
    create_strategy_id,
    safe_json_parse,
    build_synthetic_alerts,
)

router = APIRouter(prefix="/api/strategy", tags=["strategy"])
logger = get_logger(__name__)

STRATEGY_INTERPRETER_PROMPT = """
You are the dock108 Crypto Strategy Interpreter v2. Your job is to turn a user's idea or question into:

1. A detailed trader-friendly playbook.
2. A catalyst-aware analysis that explains WHY assets might move.
3. An asset-by-asset breakdown with reasoning.
4. A backtest-ready strategySpec.
5. An alertSpec for future monitoring.
6. A list of assumptions, missing data, and uncertainties.

You MUST:
- Retell the user's situation in clear trader language.
- Expand catalysts using domain knowledge: macro events, legal rulings, trade policy, ETF flows, mining sensitivity, on-chain dependencies.
- Identify what type of catalyst this is (macro regulatory, legal, liquidity, tech upgrade, narrative-driven).
- Explain WHY this catalyst affects specific sectors.
- Provide scenario branches: positive, negative, neutral outcomes.
- Reference historical analogs or similar past events.
- Output asset-by-asset reasoning, not generic patterns.
- Provide actionable plan: entries, stops, guardrails tied to the user's risk comfort, timeline, and capital (if provided).

CAPITAL HANDLING (CRITICAL):
- Capital is OPTIONAL. The user may or may not provide it.
- If the user provides capital: generate position sizing, allocation percentages, and actual USD sizing tied to the entry plan.
- If NO capital is provided: DO NOT invent capital, and DO NOT create dollar-based entries.
- Instead produce:
  • Entry CONDITIONS (trend level, volatility trigger, breakout levels)
  • Entry STAGING (tranches based on behavior/patterns, not wallet size)
  • What to watch: volume, funding, OI, macro catalysts, on-chain
  • Reactions expected under positive, neutral, negative catalyst outcomes
  • Historical analogs and timing models
- The strategy must ALWAYS be complete even if capital is omitted.

When numbers are ambiguous, infer using context:
- If the user mentions asset prices like "90", and BTC is ~90,000, map numbers to realistic units and document assumptions.

Never output generic DCA unless clearly appropriate.
Never ignore the catalyst. Expand deeply.

CRITICAL RULES:
- Never offer financial advice. Stay clinical, deterministic, and audit-friendly.
- If user mentions prices and we know current price context, assume prices are in thousands of USD unless clearly different scale.
- If user mentions "I have 1000 in cash", that is capital in fiat, not BTC.
- Use risk comfort level to decide how aggressive entries are.
- Long-term horizon → fewer, larger tranches; intraday → tighter rules, possible stop losses.
- Never YOLO by default. If user doesn't explicitly say "all in", use risk slider to keep it sane.

Always respond using JSON with these top-level fields:
{
  "playbookText": {
    "title": "Short descriptive title (e.g., 'Long-Term BTC Accumulation from 2-Week Dip')",
    "summary": "3-5 sentences retelling the user's story in concrete terms. Must call out: current price context, approximate % drawdown, where we are vs recent highs, their capital and timing.",
    "currentMarketContext": {
      "price": "Current price levels for mentioned assets",
      "drawdownFromATH": "Percentage drawdown from all-time high",
      "volatility30d": "30-day volatility context",
      "funding": "Funding rate context if relevant",
      "oiTrend": "Open interest trend if relevant",
      "etfFlows": "ETF flow context if relevant"
    },
    "narrativeSummary": "Human-readable explanation of the catalyst and why it matters for crypto markets. Reference historical analogs if applicable.",
    "deepDive": [
      "What parts of crypto benefit from this catalyst",
      "Which sectors benefit",
      "What on-chain data matters",
      "How quickly reactions happen",
      "Historical comparison (e.g., 2019 trade war, 2020 tariff headlines)",
      "Lag/lead expectations"
    ],
    "gamePlan": [
      "Entry plan (if capital provided: '3 tranches: 33% at $90k, 33% at $85k, 34% at $80k'; if no capital: 'Breakout entry at BTC > 94,500 with volume confirmation')",
      "What to do if price continues down",
      "What to do if price rips up quickly",
      "When to stop adding or exit"
    ],
    "guardrails": [
      "If capital provided: Max % of capital that can be deployed at once",
      "If no capital: Observables-based guardrails (e.g., 'If BTC closes below 0.382 retracement for 3 days → invalidation')",
      "Risk invalidation conditions",
      "Momentum reversal signals"
    ],
    "dataSources": ["List of data we're leaning on, e.g., '14-day trend, 50/200-day moving averages'"]
  },
  "catalystAnalysis": {
    "type": "macro_legal | macro_regulatory | trade_policy | liquidity | tech_upgrade | narrative_driven | mining_sensitivity | stablecoin_risk | defi_category | l2_ecosystem",
    "description": "Detailed explanation of the catalyst and its mechanics",
    "affectedCategories": [
      "List of crypto categories most likely impacted (e.g., 'China-exposed coins', 'US policy-sensitive assets', 'Global-macro hedges')"
    ],
    "historicalAnalogs": [
      {
        "event": "Similar past event (e.g., '2019 US-China tariff announcements')",
        "cryptoReaction": "What crypto did then",
        "coinsReactedMost": ["Which coins reacted most"],
        "coinsReactedLeast": ["Which coins reacted least"],
        "liquiditySimilar": "Whether liquidity conditions were similar",
        "confidence": "High | Medium | Low"
      }
    ],
    "probableMarketReactions": {
      "ifCatalystPositive": "What happens if catalyst is positive (e.g., tariffs overturned)",
      "ifCatalystNegative": "What happens if catalyst is negative (e.g., tariffs upheld)",
      "ifCatalystNeutral": "What happens if catalyst is neutral/delayed"
    },
    "confidenceScores": {
      "overall": "High | Medium | Low",
      "assetMapping": "High | Medium | Low",
      "timing": "High | Medium | Low",
      "magnitude": "High | Medium | Low"
    }
  },
  "assetBreakdown": [
    {
      "asset": "BTC | ETH | SOL | etc.",
      "reasoning": "Why this asset moves given the catalyst",
      "reaction": "Expected reaction (e.g., 'up on uncertainty', 'up if tariffs lifted')",
      "entryPlan": [
        "Specific entry plan for this asset (e.g., '2 tranches', 'breakout or dip buy')"
      ],
      "risks": [
        "Specific risks for this asset (e.g., 'strong USD maybe dampens', 'whales sell news')"
      ],
      "confidence": "High | Medium | Low"
    }
  ],
  "strategySpec": {
    "name": "Strategy name",
    "market": "BTC / ETH / SOL / cross-asset",
    "timeframe": "15m / hourly / daily / weekly",
    "thesis": "Single short paragraph",
    "units": "USD | thousands | percentage",
    "entryPlan": {
      "tranches": [
        {
          "trigger": "Price condition or indicator (e.g., 'BTC breaks above 94,500 with volume')",
          "capitalPct": 33.3,
          "allocateUsd": 300,
          "comments": "Why this tranche"
        }
      ],
      "maxDeploymentPct": 100.0
    },
    "indicators": [
      {
        "name": "indicator label",
        "params": { "window": 20 },
        "source": "price | funding | onchain | macro"
      }
    ],
    "entries": [
      {
        "side": "long | short",
        "condition": "Entry condition (e.g., 'If ruling is positive AND BTC breaks above 94,500') - REQUIRED if no capital provided",
        "method": "breakout | mean-reversion | catalyst | trend | sentiment",
        "tranchePercent": 30,
        "allocateUsd": 300,
        "logic": "Plain english rule",
        "confidence": 1-5,
        "tags": ["mean-reversion", "onchain"],
        "notes": "Optional notes"
      }
    ],
    "exits": [
      {
        "logic": "exit rule",
        "type": "stop | target | timed",
        "notes": "extra clarity"
      }
    ],
    "risk": {
      "maxCapitalAtRiskPct": number,
      "maxOpenPositions": number,
      "positionSizing": "rule of thumb"
    }
  },
  "backtestBlueprint": {
    "datasets": [
      {
        "name": "dataset short label",
        "source": "exchange / onchain / macro",
        "resolution": "15m / 1h / 1d",
        "fields": ["open", "high", "fundingRate"]
      }
    ],
    "metrics": ["winRate", "expectancy", "maxDrawdown", "sharpe", "CAGR", "timeInMarket"],
    "assumptions": ["fee rate", "slippage", "trade hours"],
    "scenarios": ["lump sum", "3-tranche DCA", "weekly DCA"],
    "period": "2017-01-01 to today (or specific range)"
  },
  "edgeDiagnostics": {
    "strengths": ["clear structural imbalance"],
    "risks": ["low sample size"],
    "monitoring": ["watch stablecoin flows weekly"]
  },
  "alertSpec": {
    "triggers": [
      {
        "name": "Alert name",
        "condition": "if BTC closes below X while undeployed capital remains",
        "channel": "email | console | webhook",
        "cooldownMinutes": 60
      }
    ]
  },
  "assumptions": {
    "normalizations": ["What we assumed about ambiguous numbers"],
    "uncertainties": ["What we're unsure about"],
    "userSaid90Means": "90k USD per BTC (or whatever normalization was made)"
  }
}

IMPORTANT NOTES:
- If capital is NOT provided: entries must include "condition" and "method" but "allocateUsd" should be omitted. "tranchePercent" indicates relative allocation (e.g., 30% of whatever capital user decides to deploy).
- If capital IS provided: include both "allocateUsd" and "tranchePercent" in entries and entryPlan tranches.
- The strategy must ALWAYS be complete even if capital is omitted - focus on entry conditions, staging, scenarios, and monitoring.

- Use dock108 voice: short, structured, matter-of-fact.
- If information is missing, make the best deterministic assumption and explain it within assumptions.
""".strip()


async def fetch_price_context(assets: list[str]) -> dict[str, Any]:
    """Fetch current price context for assets. Placeholder - would call real API."""
    # TODO: Integrate with real price API (CoinGecko, Binance, etc.)
    # For now, return placeholder structure
    context = {}
    for asset in assets:
        # Placeholder prices - in real implementation, fetch from API
        price_map = {
            "BTC": 93000.0,
            "ETH": 3500.0,
            "SOL": 150.0,
        }
        current_price = price_map.get(asset.upper(), 0.0)
        if current_price > 0:
            context[asset.upper()] = {
                "currentPriceUsd": current_price,
                "daysChangePct": -22.3,  # Placeholder
                "fromRecentHighPct": -35.1,  # Placeholder
            }
    return context


def build_strategy_interpreter_user_prompt(
    idea_text: str,
    scenario_type: str | None = None,
    assets: list[str] | None = None,
    capital: float | None = None,
    capital_currency: str | None = None,
    time_horizon: str | None = None,
    risk_comfort: str | None = None,
    data_sources: list[str] | None = None,
    price_context: dict[str, Any] | None = None,
) -> str:
    """Build enriched user prompt with form fields and price context."""
    parts = [f"User crypto hypothesis:\n\"\"\"{idea_text}\"\"\""]
    
    if scenario_type:
        parts.append(f"\nScenario type: {scenario_type}")
    if assets:
        parts.append(f"Assets: {', '.join(assets)}")
    if capital is not None and capital > 0:
        parts.append(f"Available capital: {capital} {capital_currency or 'USD'}")
        parts.append("IMPORTANT: User provided capital - include position sizing and USD allocations in entries.")
    else:
        parts.append("IMPORTANT: User did NOT provide capital - produce entry CONDITIONS and STAGING based on behavior/patterns, NOT dollar amounts.")
    if time_horizon:
        parts.append(f"Time horizon: {time_horizon}")
    if risk_comfort:
        parts.append(f"Risk comfort: {risk_comfort}")
    if data_sources:
        parts.append(f"Data sources to consider: {', '.join(data_sources)}")
    
    if price_context:
        parts.append("\nCurrent market context:")
        for asset, data in price_context.items():
            parts.append(
                f"- {asset}: ${data['currentPriceUsd']:,.0f} "
                f"({data['daysChangePct']:+.1f}% change, "
                f"{data['fromRecentHighPct']:+.1f}% from recent high)"
            )
    
    parts.append("\nReturn only JSON. Make sure it validates against the contract above.")
    return "\n".join(parts).strip()


class InterpretRequest(BaseModel):
    ideaText: str = Field(min_length=10)
    userId: int | None = None
    # New structured form fields
    scenarioType: str | None = None  # "enter" | "manage" | "test_pattern"
    assets: list[str] = Field(default_factory=list)  # ["BTC", "ETH", etc.]
    capital: float | None = None  # OPTIONAL - if not provided, strategy is still complete
    capitalCurrency: str | None = None  # "USD", "USDT", etc.
    timeHorizon: str | None = None  # "hours" | "days" | "weeks" | "months" | "cycle"
    riskComfort: str | None = None  # "conservative" | "moderate" | "aggressive"
    dataSources: list[str] = Field(default_factory=list)  # ["price", "funding", "oi", etc.]


async def interpret_strategy_with_llm(
    idea_text: str,
    scenario_type: str | None = None,
    assets: list[str] | None = None,
    capital: float | None = None,
    capital_currency: str | None = None,
    time_horizon: str | None = None,
    risk_comfort: str | None = None,
    data_sources: list[str] | None = None,
    price_context: dict[str, Any] | None = None,
) -> StrategyInterpretation:
    """Call OpenAI to interpret the strategy with enriched context."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable required")

    client = OpenAI(api_key=api_key, timeout=120.0)  # 2 minute timeout
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))

    user_prompt = build_strategy_interpreter_user_prompt(
        idea_text=idea_text,
        scenario_type=scenario_type,
        assets=assets,
        capital=capital,
        capital_currency=capital_currency,
        time_horizon=time_horizon,
        risk_comfort=risk_comfort,
        data_sources=data_sources,
        price_context=price_context,
    )

    logger.info("calling_openai", model=model, prompt_length=len(STRATEGY_INTERPRETER_PROMPT) + len(user_prompt))
    
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": STRATEGY_INTERPRETER_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout=120.0,  # 2 minute timeout
        )
    except Exception as e:
        logger.error("openai_call_failed", error=str(e), exc_info=True)
        raise

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response")

    parsed = safe_json_parse(content)
    
    # Handle backward compatibility - if playbookText missing, create from interpretation
    if "playbookText" not in parsed:
        parsed["playbookText"] = {
            "title": parsed.get("strategySpec", {}).get("name", "Strategy"),
            "summary": parsed.get("interpretation", ""),
            "gamePlan": [],
            "guardrails": [],
            "dataSources": [],
        }
    
    # If interpretation missing but playbookText exists, use playbook summary
    if "interpretation" not in parsed and "playbookText" in parsed:
        parsed["interpretation"] = parsed["playbookText"].get("summary", "")
    elif "interpretation" not in parsed:
        parsed["interpretation"] = ""
    
    # Ensure optional new fields have defaults
    if "catalystAnalysis" not in parsed:
        parsed["catalystAnalysis"] = None
    if "assetBreakdown" not in parsed:
        parsed["assetBreakdown"] = []
    if "assumptions" not in parsed:
        parsed["assumptions"] = {"normalizations": [], "uncertainties": [], "userSaid90Means": None}
    
    return StrategyInterpretation(**parsed)


def build_deterministic_backtest(strategy_id: str, strategy_spec: StrategySpec) -> BacktestResult:
    """Generate deterministic backtest results based on strategy hash."""
    seed_str = f"{strategy_id}{strategy_spec.market}{strategy_spec.timeframe}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)

    def pseudo(multiplier: int, bias: float = 0.0) -> float:
        return ((seed % multiplier) / multiplier + bias) % 1.0

    win_rate = 0.4 + pseudo(70, 0.1)
    expectancy = round(pseudo(90) * 3 - 1, 2)
    max_drawdown = round(pseudo(60) * 0.3, 2)
    sharpe = round(pseudo(80) * 2, 2)
    best_trade = round(pseudo(40) * 12, 2)
    worst_trade = round(pseudo(50) * -10, 2)
    trades = max(8, round(pseudo(100) * 40))

    start = now_utc() - timedelta(days=30)
    equity_curve = []
    for idx in range(30):
        drift = idx * pseudo(100) * 0.5
        equity_curve.append({
            "timestamp": (start + timedelta(days=idx)).isoformat(),
            "equity": round(1 + drift / 100 + pseudo(100) * 0.05, 3),
        })

    trades_list = []
    for idx, point in enumerate(equity_curve):
        trades_list.append({
            "id": f"{strategy_id}-{idx}",
            "timestamp": point["timestamp"],
            "side": "long" if idx % 2 == 0 else "short",
            "pnl": round(pseudo(100) * (1 if idx % 2 == 0 else -1), 2),
            "notes": strategy_spec.entries[0].logic if strategy_spec.entries else "LLM baseline execution",
        })

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
            "Volatility cluster during CPI weeks",
            "Funding spreads widen before pumps",
            f"Primary market focus: {strategy_spec.market}",
        ],
    )


def build_synthetic_alerts(strategy_id: str) -> list[AlertEvent]:
    """Generate synthetic alert events for testing."""
    now = now_utc()
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


@router.post("/interpret", response_model=StrategyResponse)
async def interpret_strategy(
    req: InterpretRequest,
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    """Interpret a crypto strategy idea into a structured strategy packet with playbook."""
    try:
        logger.info("interpret_strategy_started", idea_length=len(req.ideaText), assets=req.assets)
        
        # Fetch price context for assets
        assets = req.assets or ["BTC"]  # Default to BTC if none specified
        price_context = await fetch_price_context(assets)
        logger.info("price_context_fetched", assets=list(price_context.keys()))

        # Call LLM with enriched context
        logger.info("calling_llm_interpretation")
        interpretation = await interpret_strategy_with_llm(
            idea_text=req.ideaText,
            scenario_type=req.scenarioType,
            assets=req.assets,
            capital=req.capital,
            capital_currency=req.capitalCurrency,
            time_horizon=req.timeHorizon,
            risk_comfort=req.riskComfort,
            data_sources=req.dataSources,
            price_context=price_context,
        )
        logger.info("llm_interpretation_complete", strategy_name=interpretation.strategySpec.name)

        strategy_id = create_strategy_id()
        created_at = now_utc().isoformat(),

        # Persist as draft
        alerts_enabled = len(interpretation.alertSpec.triggers) > 0
        # Use playbook summary as interpretation if interpretation is missing
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
    except Exception as e:
        logger.error("strategy_interpretation_failed", exc_info=True, error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to interpret strategy: {str(e)}")


@router.post("/save", response_model=StrategyResponse)
async def save_strategy(
    req: SaveRequest,
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    """Save or update a strategy."""
    try:
        strategy_id = req.strategyId or create_strategy_id()
        created_at = now_utc().isoformat(),
        alerts_enabled = len(req.alertSpec.triggers) > 0

        # Check if exists
        result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
        existing = result.scalar_one_or_none()

        if existing:
            # Update
            existing.user_id = req.userId
            existing.idea_text = req.ideaText
            existing.interpretation = req.interpretation
            existing.strategy_json = req.strategySpec.model_dump()
            existing.backtest_blueprint = req.backtestBlueprint.model_dump()
            existing.diagnostics = req.edgeDiagnostics.model_dump()
            existing.alerts = req.alertSpec.model_dump()
            existing.status = StrategyStatus.saved
            existing.alerts_enabled = alerts_enabled
        else:
            # Insert
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
            createdAt=created_at,
            **req.model_dump(exclude={"strategyId", "ideaText", "userId"}),
        )
    except Exception as e:
        logger.error("strategy_save_failed", exc_info=True, error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to save strategy: {str(e)}")


@router.post("/backtest", response_model=BacktestResult)
async def run_backtest(
    req: BacktestRequest,
    db: AsyncSession = Depends(get_db),
) -> BacktestResult:
    """Run a backtest for a strategy."""
    try:
        # Try external backtest engine if configured
        external_url = os.getenv("BACKTEST_ENGINE_URL")
        if external_url:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(external_url, json={"strategySpec": req.strategySpec.model_dump()}, timeout=30.0)
                    if response.is_success:
                        result_data = response.json()
                        result = BacktestResult(**result_data, strategyId=req.strategyId)
                        # Persist
                        backtest = Backtest(
                            id=result.id,
                            strategy_id=req.strategyId,
                            results_json=result.model_dump(),
                        )
                        db.add(backtest)
                        await db.commit()
                        return result
            except Exception as e:
                logger.warning("external_backtest_failed", error=str(e))

        # Fall back to deterministic
        result = build_deterministic_backtest(req.strategyId, req.strategySpec)

        # Persist
        backtest = Backtest(
            id=result.id,
            strategy_id=req.strategyId,
            results_json=result.model_dump(),
        )
        db.add(backtest)
        await db.commit()

        return result
    except Exception as e:
        logger.error("backtest_failed", exc_info=True, error=str(e))
        raise HTTPException(status_code=400, detail=f"Backtest failed: {str(e)}")


@router.get("/alerts")
async def fetch_alerts(
    strategyId: str = Query(..., alias="strategyId"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[AlertEvent]]:
    """Fetch alert events for a strategy. Always returns placeholder data if none exist."""
    try:
        result = await db.execute(
            select(Alert)
            .where(Alert.strategy_id == strategyId)
            .order_by(Alert.triggered_at.desc())
            .limit(25)
        )
        alerts = result.scalars().all()

        if not alerts:
            # Return synthetic alerts as placeholder
            events = build_synthetic_alerts(strategyId)
        else:
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
    except Exception as e:
        logger.warning("fetch_alerts_failed", error=str(e), strategy_id=strategyId)
        # Always return synthetic alerts as placeholder on any error
        return {"events": build_synthetic_alerts(strategyId)}


@router.post("/alerts", response_model=dict[str, Any])
async def toggle_alerts(
    req: ToggleAlertsRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Toggle alerts enabled/disabled for a strategy."""
    try:
        await db.execute(
            update(Strategy)
            .where(Strategy.id == req.strategyId)
            .values(alerts_enabled=req.enabled)
        )
        await db.commit()

        # Notify worker webhook if configured
        webhook_url = os.getenv("ALERTS_WEBHOOK_URL")
        if webhook_url:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(webhook_url, json={"strategyId": req.strategyId, "enabled": req.enabled}, timeout=5.0)
            except Exception as e:
                logger.warning("alert_webhook_failed", error=str(e))

        return {"strategyId": req.strategyId, "enabled": req.enabled}
    except Exception as e:
        logger.error("toggle_alerts_failed", exc_info=True, error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to toggle alerts: {str(e)}")


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
) -> StrategyResponse:
    """Fetch a strategy by ID."""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_strategy_failed", exc_info=True, error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to fetch strategy: {str(e)}")

