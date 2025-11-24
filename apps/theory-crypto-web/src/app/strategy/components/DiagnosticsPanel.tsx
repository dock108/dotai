import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BacktestBlueprint, EdgeDiagnostics } from "@/types";

interface DiagnosticsPanelProps {
  diagnostics: EdgeDiagnostics;
  blueprint: BacktestBlueprint;
}

export function DiagnosticsPanel({ diagnostics, blueprint }: DiagnosticsPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Diagnostics & Blueprint</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-6 md:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Strengths</p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm">
            {diagnostics.strengths.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="mt-6 text-xs uppercase tracking-wide text-muted-foreground">Risks</p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm">
            {diagnostics.risks.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Datasets</p>
          <ul className="mt-2 space-y-2 text-sm">
            {blueprint.datasets.map((dataset) => (
              <li key={`${dataset.name}-${dataset.source}`} className="rounded-lg border border-border/70 p-3">
                <span className="font-medium">{dataset.name}</span>
                <div className="text-xs text-muted-foreground">
                  {dataset.source} • {dataset.resolution} • {dataset.fields.join(", ")}
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-6 text-xs uppercase tracking-wide text-muted-foreground">Assumptions</p>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm">
            {blueprint.assumptions.map((assumption) => (
              <li key={assumption}>{assumption}</li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

