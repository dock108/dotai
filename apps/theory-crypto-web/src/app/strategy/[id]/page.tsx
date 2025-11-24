import { notFound } from "next/navigation";
import { StrategyDetailClient } from "@/app/strategy/[id]/strategy-detail-client";
import { StrategyAPI, createClient, type StrategyResponse, type BacktestResult, type AlertEvent } from "@dock108/js-core";

interface StrategyDetailPageProps {
  params: { id: string };
}

/**
 * Strategy detail page - server component that fetches strategy data.
 * 
 * Fetches strategy, alerts, and backtest data from the theory-engine-api backend.
 * If the strategy is not found, falls back to sample data for development/testing.
 * 
 * All data fetching happens server-side for better performance and SEO.
 */
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
    const api = new StrategyAPI(createClient(baseURL));

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
  backtest: BacktestResult | undefined
): { strategy: StrategyResponse; backtest: BacktestResult | undefined; alerts: AlertEvent[] } {
  const strategy: StrategyResponse = {
    id: strategyId,
    ideaText: "BTC funding flips negative ahead of CPI and rips post print.",
    interpretation: "Fade CPI anxiety: accumulate BTC when funding goes negative pre-CPI and exit on mean reversion.",
    strategySpec: {
      name: "CPI funding squeeze",
      market: "BTC-PERP",
      timeframe: "1h",
      thesis: "Funding switches negative into macro prints, then reverses as risk turns on.",
      indicators: [
        { name: "FundingRate", source: "perp", params: { window: 6 } },
        { name: "CPIEventWindow", source: "macro", params: { hoursBefore: 12 } },
      ],
      entries: [
        {
          side: "long",
          logic: "Enter long when funding < -0.02% and CPI within 12h.",
          confidence: 4,
          tags: ["event", "perp"],
        },
      ],
      exits: [
        { logic: "Close when funding normalizes > 0.01% or +6% move", type: "target" },
      ],
      risk: {
        maxCapitalAtRiskPct: 3,
        maxOpenPositions: 1,
        positionSizing: "2.5% per trade, 1 active position.",
      },
    },
    backtestBlueprint: {
      datasets: [
        {
          name: "BTC perp funding",
          source: "FTX archive",
          resolution: "1h",
          fields: ["fundingRate", "markPrice"],
        },
        {
          name: "CPI calendar",
          source: "BLS",
          resolution: "1d",
          fields: ["eventTime"],
        },
      ],
      metrics: ["winRate", "expectancy", "maxDrawdown", "sharpe"],
      assumptions: ["Fees 2 bps", "Slippage 5 bps", "24/7 trading"],
    },
    edgeDiagnostics: {
      strengths: ["Captures predictable liquidity vacuum post CPI", "Uses funding as positioning proxy"],
      risks: ["Macro surprises break pattern", "Low sample size per quarter"],
      monitoring: ["Track ETF flows weekly", "Watch perp basis on OKX/Binance"],
    },
    alertSpec: {
      triggers: [
        {
          name: "Funding flip watcher",
          condition: "Funding < -0.02% and CPI within 12h",
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
      winRate: 58,
      expectancy: 1.2,
      maxDrawdown: 0.12,
      sharpe: 1.4,
      bestTrade: 4.3,
      worstTrade: -2.1,
      numberOfTrades: 28,
    },
    trades: [],
    regimeNotes: ["Synthetic sample when DB offline"],
  };

  return { strategy, backtest: backtest || defaultBacktest, alerts };
}
