import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import dayjs from "@/lib/dayjs";
import type { BacktestResult } from "@/types";

interface BacktestResultCardProps {
  result?: BacktestResult;
}

export function BacktestResultCard({ result }: BacktestResultCardProps) {
  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Backtest</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Run a backtest to see performance metrics.</p>
        </CardContent>
      </Card>
    );
  }

  const metrics = [
    { label: "Win rate", value: `${result.metrics.winRate}%` },
    { label: "Expectancy", value: `${result.metrics.expectancy}R` },
    { label: "Max DD", value: `${result.metrics.maxDrawdown * 100}%` },
    { label: "Sharpe", value: result.metrics.sharpe },
    { label: "Best trade", value: `${result.metrics.bestTrade}R` },
    { label: "Worst trade", value: `${result.metrics.worstTrade}R` },
    { label: "# trades", value: result.metrics.numberOfTrades },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Backtest</CardTitle>
        <p className="text-xs text-muted-foreground">Generated {dayjs(result.generatedAt).fromNow()}</p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          {metrics.map((metric) => (
            <div key={metric.label} className="rounded-lg border border-border/60 p-3 text-sm">
              <p className="text-xs uppercase text-muted-foreground">{metric.label}</p>
              <p className="mt-1 text-lg font-semibold">{metric.value}</p>
            </div>
          ))}
        </div>
        <div>
          <p className="text-xs uppercase text-muted-foreground">Regime notes</p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm">
            {result.regimeNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs uppercase text-muted-foreground">Equity curve</p>
          <div className="mt-2 flex h-32 gap-1 rounded-lg bg-muted/50 p-3">
            {result.equityCurve.map((point) => (
              <span key={point.timestamp} className="flex-1 self-end rounded-full bg-primary/40" style={{ height: `${point.equity * 60}%` }} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

