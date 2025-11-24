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

/**
 * API client configuration for strategy interpretation.
 * 
 * Uses extended timeout (2 minutes) to accommodate LLM calls which can
 * take longer than typical API requests. The client is created at module
 * level to avoid recreating it on every render.
 */
const baseURL = process.env.NEXT_PUBLIC_THEORY_ENGINE_URL || "http://localhost:8000";
const apiClient = createClient(baseURL);
apiClient.timeout = 120000; // 2 minutes for LLM interpretation
const api = new StrategyAPI(apiClient);

/**
 * Strategy builder page - main entry point for crypto strategy interpretation.
 * 
 * Provides a two-column layout:
 * - Left: Strategy form for user input (idea, capital, timeline, risk profile)
 * - Right: Tabbed results view (Playbook, Specs, Backtest)
 * 
 * On form submission, calls the theory-engine-api backend to:
 * 1. Interpret the strategy using LLM
 * 2. Generate structured playbook, specs, and backtest blueprint
 * 3. Display results in organized tabs
 * 
 * All server-side operations (LLM calls, persistence, backtesting) are
 * handled by the theory-engine-api backend. This is a thin client.
 */
export default function StrategyBuilderPage() {
  const [strategy, setStrategy] = useState<StrategyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("playbook");

  const handleSubmit = async (formData: StrategyFormData) => {
    setLoading(true);
    try {
      const result = await api.interpret(formData.ideaText, {
        scenarioType: formData.scenarioType,
        assets: formData.assets,
        capital: formData.capital ?? undefined,
        capitalCurrency: formData.capitalCurrency,
        timeHorizon: formData.timeHorizon,
        riskComfort: formData.riskComfort,
        dataSources: formData.dataSources,
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
          <p className="text-sm uppercase tracking-wide text-primary">Crypto Strategy Interpreter</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Turn a gut feeling about crypto into a testable game plan</h1>
          <p className="mt-3 text-base text-muted-foreground">
            Describe your situation, capital, and timeline. We&apos;ll convert it into a structured playbook, backtest blueprint, and alert wiring.
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
                  Fill out the form on the left to generate a full crypto strategy playbook.
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
