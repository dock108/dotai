"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

export interface StrategyFormData {
  scenarioType: string;
  ticker: string;
  includeSector: boolean;
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
  { value: "enter", label: "I want a plan to enter a stock" },
  { value: "manage", label: "I'm already in and deciding whether to add / trim / exit" },
  { value: "test_pattern", label: "I want to test a pattern or catalyst" },
];

const TIME_HORIZONS = [
  { value: "intraday", label: "Intraday" },
  { value: "swing", label: "1–7 days" },
  { value: "multi_week", label: "Multi-week" },
  { value: "multi_month", label: "Multi-month" },
  { value: "long_term", label: "Long-term (1+ years)" },
];

const RISK_LEVELS = [
  { value: "conservative", label: "Conservative" },
  { value: "moderate", label: "Moderate" },
  { value: "aggressive", label: "Aggressive" },
];

const DATA_SOURCES = [
  { value: "price", label: "Price trend" },
  { value: "volume", label: "Volume / VWAP" },
  { value: "volatility", label: "ATR / volatility" },
  { value: "sector", label: "Sector rotation" },
  { value: "etf", label: "ETF flows" },
  { value: "fed", label: "Fed policy / macro" },
  { value: "earnings", label: "Earnings revisions" },
  { value: "short", label: "Short interest" },
];

const SUGGESTIONS = [
  "NVDA earnings this week — wait for dip or buy the run-up?",
  "AAPL dropped 12% post earnings. Is this a long-term entry?",
  "If the Fed cuts twice, which sectors lead the move?",
  "High short interest + improving fundamentals = squeeze setup?",
  "What happens to AMZN if the DOJ blocks the acquisition?",
];

export function StrategyForm({ onSubmit, loading = false }: StrategyFormProps) {
  const [formData, setFormData] = useState<StrategyFormData>({
    scenarioType: "enter",
    ticker: "AAPL",
    includeSector: true,
    ideaText: "",
    capital: null,
    capitalCurrency: "USD",
    timeHorizon: "multi_week",
    riskComfort: "moderate",
    dataSources: [],
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.ideaText.length < 10 || formData.ticker.trim().length === 0) return;
    onSubmit(formData);
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
        <h2 className="text-lg font-semibold mb-4">Describe your stock situation</h2>

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

        {/* Ticker */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium">Ticker *</label>
          <input
            type="text"
            value={formData.ticker}
            onChange={(e) => setFormData((prev) => ({ ...prev, ticker: e.target.value.toUpperCase() }))}
            className="w-full rounded-md border border-border px-3 py-2 text-sm uppercase"
            placeholder="e.g. NVDA, AAPL, TSLA"
          />
            <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2">
            <div>
              <p className="text-sm font-medium">Consider sector & ETF exposure</p>
              <p className="text-xs text-muted-foreground">
                When enabled, the interpreter will map sector behavior (XLK, XLI, XLF, etc.) and factor rotations.
              </p>
            </div>
              <Switch
                checked={formData.includeSector}
                onClick={() => setFormData((prev) => ({ ...prev, includeSector: !prev.includeSector }))}
              />
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
            placeholder="NVDA reports earnings Thursday. Should I wait for a post-earnings dip or buy the run-up?"
            value={formData.ideaText}
            onChange={(e) => setFormData((prev) => ({ ...prev, ideaText: e.target.value }))}
            rows={4}
          />
          <p className="text-xs text-muted-foreground">
            Mention catalysts (earnings, CPI, Fed decisions, guidance), sector rotations, valuation context, or technical levels. Capital is optional —
            you&apos;ll still get a complete plan.
          </p>
        </div>

        {/* Capital - Optional */}
        <div className="grid gap-4 mb-6 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Available capital <span className="text-muted-foreground">(optional)</span>
            </label>
            <input
              type="number"
              value={formData.capital ?? ""}
              onChange={(e) => setFormData((prev) => ({ ...prev, capital: e.target.value ? parseFloat(e.target.value) : null }))}
              className="w-full rounded-md border border-border px-3 py-2 text-sm"
              placeholder="5000"
            />
            <p className="text-xs text-muted-foreground">Leave blank for pattern-only strategy.</p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Currency</label>
            <select
              value={formData.capitalCurrency}
              onChange={(e) => setFormData((prev) => ({ ...prev, capitalCurrency: e.target.value }))}
              className="w-full rounded-md border border-border px-3 py-2 text-sm"
              disabled={!formData.capital}
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
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

        <Button type="submit" disabled={loading || formData.ideaText.length < 10 || !formData.ticker.trim()} className="w-full">
          {loading ? "Building Strategy..." : "Build Strategy"}
        </Button>
      </Card>
    </form>
  );
}

