"use client";

import { useState } from "react";
import { StrategyForm, type StrategyFormData } from "@/app/strategy/components/StrategyForm";
import { PlaybookTab } from "@/app/strategy/components/PlaybookTab";
import { SpecsTab } from "@/app/strategy/components/SpecsTab";
import { BacktestTab } from "@/app/strategy/components/BacktestTab";
import { Tabs } from "@/components/ui/tabs";
import { StrategyAPI, createClient } from "@dock108/js-core";
import type { StrategyResponse } from "@dock108/js-core";
import { toast } from "sonner";

const baseURL = process.env.NEXT_PUBLIC_THEORY_ENGINE_URL || "http://localhost:8000";
// Create client with longer timeout for LLM calls (2 minutes)
const apiClient = createClient(baseURL);
// Override timeout for strategy API - LLM calls can take longer
apiClient.timeout = 120000; // 2 minutes
const api = new StrategyAPI(apiClient, "/api/stocks/strategy");

export default function StrategyBuilderPage() {
  const [strategy, setStrategy] = useState<StrategyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("playbook");

  const handleSubmit = async (formData: StrategyFormData) => {
    setLoading(true);
    try {
      const result = await api.interpret(formData.ideaText, {
        ticker: formData.ticker,
        scenarioType: formData.scenarioType,
        capital: formData.capital ?? undefined,
        capitalCurrency: formData.capitalCurrency,
        timeHorizon: formData.timeHorizon,
        riskComfort: formData.riskComfort,
        dataSources: formData.dataSources,
        includeSector: formData.includeSector,
      });

      setStrategy(result);
      setActiveTab("playbook"); // Default to playbook tab
      toast.success("Strategy built", { description: result.playbookText?.title || result.strategySpec.name });
    } catch (error) {
      toast.error("Failed to build strategy", {
        description: error instanceof Error ? error.message : "Please try again with more specific details.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <p className="text-sm uppercase tracking-wide text-primary">Stocks Strategy Interpreter</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Turn a catalyst or pattern into a tradable stock plan</h1>
          <p className="mt-3 text-base text-muted-foreground">
            Describe earnings setups, macro scenarios, or valuation swings. We&apos;ll return a catalyst-aware playbook, backtest blueprint, and alert wiring
            for equities.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,0.42fr)_minmax(0,0.58fr)]">
          {/* Left: Form */}
          <section>
            <StrategyForm onSubmit={handleSubmit} loading={loading} />
          </section>

          {/* Right: Results with Tabs */}
          <section>
            {!strategy ? (
              <div className="rounded-2xl border border-dashed border-border/70 p-12 text-center">
                <p className="text-sm text-muted-foreground">
                  Fill out the form on the left to generate a full stock strategy playbook.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <Tabs
                  options={[
                    { value: "playbook", label: "Playbook" },
                    { value: "specs", label: "Specs" },
                    { value: "backtest", label: "Backtest" },
                  ]}
                  value={activeTab}
                  onChange={setActiveTab}
                />

                {activeTab === "playbook" && strategy.playbookText && (
                  <PlaybookTab
                    playbook={strategy.playbookText}
                    catalystAnalysis={strategy.catalystAnalysis}
                    assetBreakdown={strategy.assetBreakdown}
                  />
                )}

                {activeTab === "specs" && (
                  <SpecsTab
                    strategySpec={strategy.strategySpec}
                    backtestBlueprint={strategy.backtestBlueprint}
                    alertSpec={strategy.alertSpec}
                    assumptions={strategy.assumptions}
                    catalystAnalysis={strategy.catalystAnalysis}
                  />
                )}

                {activeTab === "backtest" && <BacktestTab blueprint={strategy.backtestBlueprint} />}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
