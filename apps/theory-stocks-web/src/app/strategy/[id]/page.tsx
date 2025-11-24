import { notFound } from "next/navigation";
import { StrategyDetailClient } from "@/app/strategy/[id]/strategy-detail-client";
import { StrategyAPI, createClient, type StrategyResponse, type BacktestResult, type AlertEvent } from "@dock108/js-core";

interface StrategyDetailPageProps {
  params: { id: string };
}

export default async function StrategyDetailPage({ params }: StrategyDetailPageProps) {
  const data = await fetchStrategyBundle(params.id);
  if (!data) {
    notFound();
  }
  return <StrategyDetailClient strategy={data.strategy} backtest={data.backtest} alerts={data.alerts} />;
}

async function fetchStrategyBundle(strategyId: string) {
  try {
    const baseURL = process.env.NEXT_PUBLIC_THEORY_ENGINE_URL || "http://localhost:8000";
    const api = new StrategyAPI(createClient(baseURL), "/api/stocks/strategy");

    // Fetch strategy and alerts
    const [strategy, alerts] = await Promise.all([
      api.get(strategyId).catch(() => null),
      api.fetchAlerts(strategyId).catch(() => [] as AlertEvent[]),
    ]);

    // If strategy not found, return sample data
    if (!strategy) {
      return buildSampleStrategy(strategyId, alerts, undefined);
    }

    // Backtest would need a separate GET endpoint - for now return undefined
    const backtest = undefined as BacktestResult | undefined;

    return { strategy, backtest, alerts };
  } catch (error) {
    console.warn("Failed to load strategy detail", error);
    return buildSampleStrategy(strategyId, [], undefined);
  }
}

function buildSampleStrategy(
  strategyId: string,
  alerts: AlertEvent[],
  backtest: BacktestResult | undefined,
): { strategy: StrategyResponse; backtest: BacktestResult | undefined; alerts: AlertEvent[] } {
  const strategy: StrategyResponse = {
    id: strategyId,
    ideaText: "NVDA reports earnings next week. Should I wait for a post-print dip or position into the run-up?",
    interpretation:
      "Treat NVDA earnings as a catalyst trade: stage entries on confirmation above 925 with volume, or buy retraces into 870–890 if the reaction is neutral.",
    playbookText: {
      title: "NVDA earnings elasticity",
      summary: "Use the earnings beat as the driver: chase only on legit volume, or buy the controlled retrace into the prior range.",
      currentMarketContext: {
        price: "NVDA trading near $910, -6% from highs",
        drawdownFromATH: "-6%",
        volatility30d: "ATR rising to 21 points",
        etfFlows: "XLK inflows +$1.2B WoW",
      },
      narrativeSummary:
        "Tech leadership and AI demand keep NVDA bid, but expectations are sky-high. Earnings beats typically gap up, then chop for ~10 days before setting a sustained direction.",
      deepDive: [
        "Valuation stretching back toward 45x forward PE",
        "Macro sensitivity: 10y yield bull flag could cap upside if it breaks higher",
        "Sector rotation: XLK vs SPY remains constructive, but breadth is narrow",
        "Historical analog: last four NVDA beats rallied 5-10% intraday then faded to retest support within a week",
        "Timing model: best RR occurs buying the first controlled retrace post-print",
      ],
      gamePlan: [
        "If NVDA rips on earnings with volume >1.3x, chase only on confirmation above 925",
        "If reaction is muted, bid the 870–890 range with tight invalidation",
        "If macro goes risk-off (rates spike), stand down until NVDA rebuilds structure",
        "Exit partial into 980–1000 supply or if price closes <850 twice",
      ],
      guardrails: [
        "No trade if volume is <1.1x on breakout",
        "Fail on closes <850 (two sessions) or if SOXX/XLK diverge sharply lower",
      ],
      dataSources: ["Daily candles", "Volume trend", "ETF flows", "Rates context"],
    },
    strategySpec: {
      name: "NVDA earnings elasticity",
      market: "equities",
      timeframe: "multi-week",
      thesis:
        "NVIDIA tends to gap higher on beats, then chops for ~2 weeks. Funding positioning favors a breakout continuation only when volume expands >1.3x.",
      ticker: "NVDA",
      sector: "Technology",
      indicators: [
        { name: "VolumeSurge", source: "price", params: { multiple: 1.3 } },
        { name: "PostEarningsDrift", source: "event", params: { days: 10 } },
      ],
      entries: [
        {
          side: "long",
          condition: "If earnings beat AND NVDA reclaims 925 with 1.3x average volume",
          method: "catalyst",
          tranchePercent: 50,
          logic: "Breakout continuation only when buyers confirm the move.",
          confidence: 4,
          tags: ["earnings", "breakout"],
        },
        {
          side: "long",
          condition: "If reaction is muted and NVDA retests 870–890 support within 5 sessions",
          method: "mean-reversion",
          tranchePercent: 50,
          logic: "Buy the range re-entry when implied vol collapses.",
          confidence: 3,
          tags: ["mean-reversion"],
        },
      ],
      exits: [
        { logic: "Trim into 980–1000 supply" , type: "target" },
        { logic: "Invalidate if NVDA closes < 850 for 2 sessions", type: "stop" },
      ],
      risk: {
        maxCapitalAtRiskPct: 4,
        maxOpenPositions: 2,
        positionSizing: "Split entries 50/50 between breakout and pullback plan.",
      },
    },
    backtestBlueprint: {
      datasets: [
        {
          name: "NVDA daily candles",
          source: "Polygon",
          resolution: "1d",
          fields: ["open", "high", "low", "close", "volume"],
        },
        {
          name: "Earnings calendar",
          source: "WallStreetHorizon",
          resolution: "event",
          fields: ["eventTime", "surprisePct"],
        },
      ],
      metrics: ["winRate", "expectancy", "maxDrawdown", "sharpe", "postEarningsDrift"],
      assumptions: ["$0.01/share commission", "0.05% slippage", "No overnight leverage"],
      scenarios: ["earnings breakout", "post-earnings dip buy", "failed breakout fade"],
      period: "2018-01-01 to today",
    },
    edgeDiagnostics: {
      strengths: [
        "Maps the exact behavior NVDA shows after beats (gap + drift).",
        "Uses volume confirmation to avoid chasing weak reactions.",
      ],
      risks: ["Macro risk-off can override earnings strength", "High expectations make upside asymmetric"],
      monitoring: ["Track SOXX vs SPY rotation", "Watch implied vol crush after the call"],
    },
    alertSpec: {
      triggers: [
        {
          name: "Volume breakout watcher",
          condition: "Alert if NVDA trades >1.3x 20d volume while reclaiming 925",
          channel: "console",
          cooldownMinutes: 90,
        },
        {
          name: "Earnings dip zone",
          condition: "Alert if NVDA trades between 870–890 within 3 sessions after earnings",
          channel: "console",
          cooldownMinutes: 60,
        },
      ],
    },
    createdAt: new Date().toISOString(),
  };

  const defaultBacktest: BacktestResult = {
    id: `bt_${strategyId}`,
    strategyId,
    generatedAt: new Date().toISOString(),
    equityCurve: [],
    metrics: {
      winRate: 61,
      expectancy: 0.85,
      maxDrawdown: 0.09,
      sharpe: 1.3,
      bestTrade: 5.4,
      worstTrade: -3.1,
      numberOfTrades: 32,
    },
    trades: [],
    regimeNotes: ["Synthetic NVDA earnings playbook sample"],
  };

  return { strategy, backtest: backtest || defaultBacktest, alerts };
}
