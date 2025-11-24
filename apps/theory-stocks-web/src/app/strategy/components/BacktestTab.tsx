"use client";

import type { BacktestBlueprint } from "@dock108/js-core";
import { Card } from "@/components/ui/card";

interface BacktestTabProps {
  blueprint: BacktestBlueprint;
}

export function BacktestTab({ blueprint }: BacktestTabProps) {
  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Backtest Blueprint</h2>
        <p className="text-sm text-muted-foreground mb-6">
          We&apos;ll plug this strategy into the backtest engine soon. For now, here&apos;s the blueprint of what
          we&apos;d test.
        </p>

        {blueprint.period && (
          <div className="mb-4 p-4 bg-muted rounded-lg">
            <p className="text-sm">
              <span className="font-semibold">Period:</span> {blueprint.period}
            </p>
          </div>
        )}

        {blueprint.scenarios && blueprint.scenarios.length > 0 && (
          <div className="mb-4 p-4 bg-muted rounded-lg">
            <p className="text-sm font-semibold mb-2">Scenarios:</p>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {blueprint.scenarios.map((scenario, idx) => (
                <li key={idx}>{scenario}</li>
              ))}
            </ul>
          </div>
        )}

        {blueprint.metrics.length > 0 && (
          <div className="mb-4 p-4 bg-muted rounded-lg">
            <p className="text-sm font-semibold mb-2">Metrics to calculate:</p>
            <p className="text-sm">{blueprint.metrics.join(", ")}</p>
          </div>
        )}

        {blueprint.datasets.length > 0 && (
          <div className="mb-4 p-4 bg-muted rounded-lg">
            <p className="text-sm font-semibold mb-2">Data sources:</p>
            <div className="space-y-2">
              {blueprint.datasets.map((dataset, idx) => (
                <div key={idx} className="text-sm">
                  <span className="font-medium">{dataset.name}</span> ({dataset.source}, {dataset.resolution})
                </div>
              ))}
            </div>
          </div>
        )}

        {blueprint.assumptions.length > 0 && (
          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm font-semibold mb-2">Assumptions:</p>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {blueprint.assumptions.map((assumption, idx) => (
                <li key={idx}>{assumption}</li>
              ))}
            </ul>
          </div>
        )}
      </Card>
    </div>
  );
}

