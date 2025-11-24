"use client";

import { useState } from "react";
import { StrategyCard } from "@/app/strategy/components/StrategyCard";
import { JSONSpecViewer } from "@/app/strategy/components/JSONSpecViewer";
import { DiagnosticsPanel } from "@/app/strategy/components/DiagnosticsPanel";
import { BacktestResultCard } from "@/app/strategy/components/BacktestResultCard";
import { AlertsPanel } from "@/app/strategy/components/AlertsPanel";
import { Tabs } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import type { AlertEvent, BacktestResult, StrategyResponse } from "@/types";
import { fetchAlerts, runBacktest, toggleAlerts } from "@/lib/api/strategyClient";
import { toast } from "sonner";

interface StrategyDetailClientProps {
  strategy: StrategyResponse;
  backtest?: BacktestResult;
  alerts: AlertEvent[];
}

/**
 * Strategy detail client component with tabbed interface.
 * 
 * Displays comprehensive strategy information including:
 * - Overview: Strategy card with key information
 * - Specs: JSON viewer for strategy specification
 * - Diagnostics: Edge diagnostics and blueprint analysis
 * - Backtest: Backtest results with metrics and equity curve
 * - Alerts: Alert history and toggle controls
 * 
 * Supports running backtests and toggling alerts on/off via API calls
 * to the theory-engine-api backend.
 */
export function StrategyDetailClient({ strategy, backtest, alerts }: StrategyDetailClientProps) {
  const [activeTab, setActiveTab] = useState("overview");
  const [localBacktest, setLocalBacktest] = useState(backtest);
  const [localAlerts, setLocalAlerts] = useState(alerts);
  const [alertsEnabled, setAlertsEnabled] = useState(strategy.alertSpec.triggers.length > 0);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [alertsLoading, setAlertsLoading] = useState(false);

  const handleRunBacktest = async () => {
    try {
      setBacktestLoading(true);
      const result = await runBacktest(strategy.id, strategy.strategySpec);
      setLocalBacktest(result);
      toast.success("Backtest refreshed");
    } catch (error) {
      toast.error("Backtest failed", { description: error instanceof Error ? error.message : undefined });
    } finally {
      setBacktestLoading(false);
    }
  };

  const handleToggleAlerts = async (enabled: boolean) => {
    try {
      setAlertsLoading(true);
      await toggleAlerts(strategy.id, enabled);
      setAlertsEnabled(enabled);
      toast.success(`Alerts ${enabled ? "enabled" : "disabled"}`);
    } catch (error) {
      toast.error("Alert toggle failed", { description: error instanceof Error ? error.message : undefined });
    } finally {
      setAlertsLoading(false);
    }
  };

  const handleRefreshAlerts = async () => {
    const events = await fetchAlerts(strategy.id);
    setLocalAlerts(events);
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Strategy</p>
          <h1 className="text-3xl font-semibold">{strategy.strategySpec.name}</h1>
        </div>
        <div className="flex gap-3">
          <Button onClick={handleRunBacktest} disabled={backtestLoading}>
            {backtestLoading ? "Running..." : "Run Backtest"}
          </Button>
          <Button variant="outline" onClick={() => handleToggleAlerts(!alertsEnabled)} disabled={alertsLoading}>
            {alertsEnabled ? "Disable Alerts" : "Enable Alerts"}
          </Button>
        </div>
      </div>

      <Tabs
        value={activeTab}
        onChange={setActiveTab}
        options={[
          { label: "Overview", value: "overview" },
          { label: "Backtest", value: "backtest" },
          { label: "Alerts", value: "alerts" },
        ]}
      />

      {activeTab === "overview" && (
        <div className="space-y-6">
          <StrategyCard strategy={strategy} />
          <Accordion type="multiple" className="rounded-2xl border border-border/60 bg-card/60 shadow">
            <AccordionItem value="interpretation">
              <AccordionTrigger>Interpretation</AccordionTrigger>
              <AccordionContent>
                <p className="text-sm leading-relaxed">{strategy.interpretation}</p>
              </AccordionContent>
            </AccordionItem>
            <AccordionItem value="json">
              <AccordionTrigger>Strategy JSON</AccordionTrigger>
              <AccordionContent>
                <JSONSpecViewer title="strategySpec" data={strategy.strategySpec} />
              </AccordionContent>
            </AccordionItem>
            <AccordionItem value="diagnostics">
              <AccordionTrigger>Diagnostics</AccordionTrigger>
              <AccordionContent>
                <DiagnosticsPanel diagnostics={strategy.edgeDiagnostics} blueprint={strategy.backtestBlueprint} />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      )}

      {activeTab === "backtest" && <BacktestResultCard result={localBacktest} />}

      {activeTab === "alerts" && (
        <AlertsPanel
          alertSpec={strategy.alertSpec}
          alerts={localAlerts}
          alertsEnabled={alertsEnabled}
          isToggling={alertsLoading}
          onToggle={handleToggleAlerts}
          onRefresh={handleRefreshAlerts}
        />
      )}
    </div>
  );
}

