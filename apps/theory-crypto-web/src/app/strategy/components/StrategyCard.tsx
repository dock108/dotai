import dayjs from "@/lib/dayjs";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { StrategyResponse } from "@/types";

interface StrategyCardProps {
  strategy: StrategyResponse;
  actions?: React.ReactNode;
}

export function StrategyCard({ strategy, actions }: StrategyCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <Badge className="mb-2 w-fit">Strategy blueprint</Badge>
          <CardTitle>{strategy.strategySpec.name}</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">{strategy.interpretation}</p>
          <div className="mt-2 text-xs text-muted-foreground">
            Generated {strategy.createdAt ? dayjs(strategy.createdAt).fromNow() : "just now"}
          </div>
        </div>
        {actions}
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Market</p>
          <p className="text-base font-semibold">{strategy.strategySpec.market}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Timeframe</p>
          <p className="text-base font-semibold">{strategy.strategySpec.timeframe}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Risk</p>
          <p className="text-base font-semibold">
            {strategy.strategySpec.risk.maxCapitalAtRiskPct}% cap / {strategy.strategySpec.risk.maxOpenPositions} positions
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

