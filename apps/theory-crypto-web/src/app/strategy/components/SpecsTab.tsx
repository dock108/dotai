"use client";

import type { StrategySpec, BacktestBlueprint, AlertSpec, Assumptions, CatalystAnalysis } from "@dock108/js-core";
import { Card } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { JSONSpecViewer } from "./JSONSpecViewer";

interface SpecsTabProps {
  strategySpec: StrategySpec;
  backtestBlueprint: BacktestBlueprint;
  alertSpec: AlertSpec;
  assumptions?: Assumptions;
  catalystAnalysis?: CatalystAnalysis;
}

export function SpecsTab({ strategySpec, backtestBlueprint, alertSpec, assumptions, catalystAnalysis }: SpecsTabProps) {
  return (
    <div className="space-y-4">
      <Accordion type="multiple" className="w-full">
        {catalystAnalysis && (
          <AccordionItem value="catalyst">
            <AccordionTrigger>Catalyst Analysis</AccordionTrigger>
            <AccordionContent>
              <JSONSpecViewer title="catalystAnalysis" data={catalystAnalysis} />
            </AccordionContent>
          </AccordionItem>
        )}
        <AccordionItem value="strategy">
          <AccordionTrigger>Strategy Spec</AccordionTrigger>
          <AccordionContent>
            <JSONSpecViewer title="strategySpec" data={strategySpec} />
            {strategySpec.entryPlan && (
              <div className="mt-4 p-4 bg-muted rounded-lg">
                <h4 className="font-semibold mb-2">Entry Plan</h4>
                <div className="space-y-2 text-sm">
                  {strategySpec.entryPlan.tranches.map((tranche, idx) => (
                    <div key={idx} className="border-l-2 border-primary pl-3">
                      <p className="font-medium">Tranche {idx + 1}: {tranche.capitalPct}%</p>
                      <p className="text-muted-foreground">Trigger: {tranche.trigger}</p>
                      {tranche.comments && <p className="text-muted-foreground">{tranche.comments}</p>}
                    </div>
                  ))}
                  <p className="text-xs text-muted-foreground mt-2">
                    Max deployment: {strategySpec.entryPlan.maxDeploymentPct}%
                  </p>
                </div>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="backtest">
          <AccordionTrigger>Backtest Blueprint</AccordionTrigger>
          <AccordionContent>
            <JSONSpecViewer title="backtestBlueprint" data={backtestBlueprint} />
            {backtestBlueprint.period && (
              <div className="mt-4 p-4 bg-muted rounded-lg">
                <p className="text-sm">
                  <span className="font-semibold">Period:</span> {backtestBlueprint.period}
                </p>
              </div>
            )}
            {backtestBlueprint.scenarios && backtestBlueprint.scenarios.length > 0 && (
              <div className="mt-2 p-4 bg-muted rounded-lg">
                <p className="text-sm">
                  <span className="font-semibold">Scenarios:</span> {backtestBlueprint.scenarios.join(", ")}
                </p>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="alerts">
          <AccordionTrigger>Alert Spec</AccordionTrigger>
          <AccordionContent>
            <JSONSpecViewer title="alertSpec" data={alertSpec} />
          </AccordionContent>
        </AccordionItem>

        {assumptions && (
          <AccordionItem value="assumptions">
            <AccordionTrigger>Assumptions & Normalizations</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4">
                {assumptions.normalizations.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">Normalizations</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {assumptions.normalizations.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {assumptions.uncertainties.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">Uncertainties</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {assumptions.uncertainties.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {assumptions.userSaid90Means && (
                  <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                    <p className="text-sm">
                      <span className="font-semibold">Price normalization:</span> {assumptions.userSaid90Means}
                    </p>
                  </div>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}
      </Accordion>
    </div>
  );
}

