"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";

/**
 * Form data structure for strategy interpretation input.
 * 
 * Captures user's scenario, capital, risk profile, and idea text
 * to send to the backend for LLM-based strategy interpretation.
 */
export interface StrategyFormData {
  scenarioType: string;
  assets: string[];
  ideaText: string;
  capital: number | null;
  capitalCurrency: string;
  timeHorizon: string;
  riskComfort: string;
  dataSources: string[];
}

interface StrategyFormProps {
  onSubmit: (data: StrategyFormData) => void;
  loading?: boolean;
}

const SCENARIO_TYPES = [
  { value: "enter", label: "I have cash and want a plan to enter" },
  { value: "manage", label: "I'm already in and deciding whether to add / trim / exit" },
  { value: "test_pattern", label: "I have a pattern or theory I want to test" },
];

const ASSETS = ["BTC", "ETH", "SOL", "BNB", "ADA", "AVAX", "DOT", "MATIC"];

const TIME_HORIZONS = [
  { value: "hours", label: "Hours" },
  { value: "days", label: "Days" },
  { value: "weeks", label: "Weeks" },
  { value: "months", label: "Months" },
  { value: "cycle", label: "Cycle/Bull run" },
];

const RISK_LEVELS = [
  { value: "conservative", label: "Conservative" },
  { value: "moderate", label: "Moderate" },
  { value: "aggressive", label: "Aggressive" },
];

const DATA_SOURCES = [
  { value: "price", label: "Price trend" },
  { value: "funding", label: "Funding rates" },
  { value: "oi", label: "Open interest" },
  { value: "onchain", label: "On-chain flows" },
  { value: "etf", label: "ETF flows" },
  { value: "macro", label: "Macro events (CPI/Fed)" },
];

const SUGGESTIONS = [
  "BTC dips before CPI then recovers within 3 days",
  "ETH runs after gas fees fall below 20",
  "SOL rallies on high OI + positive funding",
  "Fear & Greed below 20 = accumulate BTC",
  "Layer 2s pump after mainnet upgrade date",
];

export function StrategyForm({ onSubmit, loading = false }: StrategyFormProps) {
  const [formData, setFormData] = useState<StrategyFormData>({
    scenarioType: "enter",
    assets: ["BTC"],
    ideaText: "",
    capital: null,
    capitalCurrency: "USD",
    timeHorizon: "weeks",
    riskComfort: "moderate",
    dataSources: [],
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.ideaText.length < 10) return;
    onSubmit(formData);
  };

  const toggleAsset = (asset: string) => {
    setFormData((prev) => ({
      ...prev,
      assets: prev.assets.includes(asset) ? prev.assets.filter((a) => a !== asset) : [...prev.assets, asset],
    }));
  };

  const toggleDataSource = (source: string) => {
    setFormData((prev) => ({
      ...prev,
      dataSources: prev.dataSources.includes(source)
        ? prev.dataSources.filter((s) => s !== source)
        : [...prev.dataSources, source],
    }));
  };

  const applySuggestion = (suggestion: string) => {
    setFormData((prev) => ({ ...prev, ideaText: suggestion }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">Describe your crypto situation</h2>

        {/* Scenario Type */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium">Scenario type *</label>
          <div className="space-y-2">
            {SCENARIO_TYPES.map((type) => (
              <label key={type.value} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="scenarioType"
                  value={type.value}
                  checked={formData.scenarioType === type.value}
                  onChange={(e) => setFormData((prev) => ({ ...prev, scenarioType: e.target.value }))}
                  className="w-4 h-4"
                />
                <span className="text-sm">{type.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Assets */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium">Asset & market *</label>
          <div className="flex flex-wrap gap-2">
            {ASSETS.map((asset) => (
              <button
                key={asset}
                type="button"
                onClick={() => toggleAsset(asset)}
                className={`px-3 py-1.5 rounded-full text-sm border transition ${
                  formData.assets.includes(asset)
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border hover:border-primary"
                }`}
              >
                {asset}
              </button>
            ))}
          </div>
        </div>

        {/* Suggestions */}
        <div className="space-y-3 mb-6">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Suggestion chips</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => applySuggestion(suggestion)}
                className="rounded-full border border-border/60 px-3 py-1 text-sm text-muted-foreground transition hover:border-primary hover:text-primary"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>

        {/* Idea Text */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium">Idea text *</label>
          <Textarea
            placeholder="BTC has dumped for 2 weeks from ~120k to ~90k. I'll have $1,000 in cash on Friday. Long-term bull. Should I buy all at once or DCA as it drops?"
            value={formData.ideaText}
            onChange={(e) => setFormData((prev) => ({ ...prev, ideaText: e.target.value }))}
            rows={4}
          />
            <p className="text-xs text-muted-foreground">
            Mention: rough price levels, timing (days/weeks/months), catalysts, patterns, or market structure. Capital is optional - you can get a complete strategy without it.
          </p>
        </div>

        {/* Capital - Optional */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Available capital <span className="text-muted-foreground">(optional)</span>
            </label>
            <input
              type="number"
              value={formData.capital || ""}
              onChange={(e) => setFormData((prev) => ({ ...prev, capital: e.target.value ? parseFloat(e.target.value) : null }))}
              className="w-full px-3 py-2 border border-border rounded-md"
              placeholder="1000"
            />
            <p className="text-xs text-muted-foreground">
              Leave blank to get pattern-based strategy without position sizing
            </p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Currency</label>
            <select
              value={formData.capitalCurrency}
              onChange={(e) => setFormData((prev) => ({ ...prev, capitalCurrency: e.target.value }))}
              className="w-full px-3 py-2 border border-border rounded-md"
              disabled={!formData.capital}
            >
              <option value="USD">USD</option>
              <option value="USDT">USDT</option>
              <option value="USDC">USDC</option>
            </select>
          </div>
        </div>

        {/* Time Horizon */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium">Time horizon *</label>
          <div className="flex flex-wrap gap-2">
            {TIME_HORIZONS.map((horizon) => (
              <button
                key={horizon.value}
                type="button"
                onClick={() => setFormData((prev) => ({ ...prev, timeHorizon: horizon.value }))}
                className={`px-3 py-1.5 rounded-full text-sm border transition ${
                  formData.timeHorizon === horizon.value
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border hover:border-primary"
                }`}
              >
                {horizon.label}
              </button>
            ))}
          </div>
        </div>

        {/* Risk Comfort */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium">Risk comfort *</label>
          <div className="flex gap-2">
            {RISK_LEVELS.map((level) => (
              <button
                key={level.value}
                type="button"
                onClick={() => setFormData((prev) => ({ ...prev, riskComfort: level.value }))}
                className={`flex-1 px-3 py-2 rounded-md text-sm border transition ${
                  formData.riskComfort === level.value
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border hover:border-primary"
                }`}
              >
                {level.label}
              </button>
            ))}
          </div>
        </div>

        {/* Data Sources */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium">Data to consider (optional)</label>
          <div className="flex flex-wrap gap-2">
            {DATA_SOURCES.map((source) => (
              <button
                key={source.value}
                type="button"
                onClick={() => toggleDataSource(source.value)}
                className={`px-3 py-1.5 rounded-full text-sm border transition ${
                  formData.dataSources.includes(source.value)
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border hover:border-primary"
                }`}
              >
                {source.label}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <Button type="submit" disabled={loading || formData.ideaText.length < 10} className="w-full">
          {loading ? "Building Strategy..." : "Build Strategy"}
        </Button>
      </Card>
    </form>
  );
}

