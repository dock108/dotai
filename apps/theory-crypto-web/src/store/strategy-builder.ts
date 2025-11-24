/**
 * Zustand store for strategy builder state management.
 * 
 * Manages the lifecycle of strategy interpretation, persistence, backtesting,
 * and alert management. All API calls are delegated to the centralized
 * strategyClient module.
 * 
 * This store is used by components that need to share strategy state
 * across the application, though the main strategy builder page uses local
 * state for simplicity.
 */

import { create } from "zustand";
import {
  interpretStrategy,
  saveStrategy as saveStrategyRequest,
  runBacktest as runBacktestRequest,
  fetchAlerts as fetchAlertsRequest,
  toggleAlerts as toggleAlertsRequest,
} from "@/lib/api/strategyClient";
import type { AlertEvent, BacktestResult, StrategyResponse } from "@dock108/js-core";

/**
 * Pre-defined strategy suggestion prompts for quick input.
 */
export const STRATEGY_SUGGESTIONS = [
  "BTC dips before CPI then recovers strongly",
  "ETH pumps after gas fees drop below 20",
  "SOL rallies when OI spikes 15% in a day",
  "Fear and greed below 20 = opportunity",
  "BTC is correlated with ETF inflow surges",
];

interface StrategyBuilderState {
  ideaText: string;
  isInterpreting: boolean;
  isSaving: boolean;
  isBacktesting: boolean;
  isTogglingAlerts: boolean;
  strategy?: StrategyResponse;
  backtest?: BacktestResult;
  alerts: AlertEvent[];
  alertsEnabled: boolean;
  error?: string;
  setIdeaText: (text: string) => void;
  runInterpretation: (idea: string, userId?: number) => Promise<StrategyResponse>;
  saveCurrentStrategy: () => Promise<StrategyResponse>;
  runBacktest: () => Promise<BacktestResult>;
  refreshAlerts: () => Promise<void>;
  toggleAlerts: (enabled: boolean) => Promise<void>;
}

export const useStrategyBuilderStore = create<StrategyBuilderState>((set, get) => ({
  ideaText: "",
  isInterpreting: false,
  isSaving: false,
  isBacktesting: false,
  isTogglingAlerts: false,
  alerts: [],
  alertsEnabled: false,
  setIdeaText: (text) => set({ ideaText: text }),
  async runInterpretation(idea, userId) {
    set({ isInterpreting: true, error: undefined });
    try {
      const data = await interpretStrategy(idea, { userId });
      set({ strategy: data, ideaText: idea, alertsEnabled: data.alertSpec.triggers.length > 0 });
      return data;
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Failed to interpret strategy" });
      throw error;
    } finally {
      set({ isInterpreting: false });
    }
  },
  async saveCurrentStrategy() {
    const state = get();
    if (!state.strategy) {
      throw new Error("No strategy to save");
    }
    set({ isSaving: true, error: undefined });
    try {
      const saved = await saveStrategyRequest({
        strategyId: state.strategy.id,
        ideaText: state.ideaText,
        interpretation: state.strategy.interpretation,
        strategySpec: state.strategy.strategySpec,
        backtestBlueprint: state.strategy.backtestBlueprint,
        edgeDiagnostics: state.strategy.edgeDiagnostics,
        alertSpec: state.strategy.alertSpec,
      });
      set({ strategy: saved });
      return saved;
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Failed to save strategy" });
      throw error;
    } finally {
      set({ isSaving: false });
    }
  },
  async runBacktest() {
    const state = get();
    if (!state.strategy) {
      throw new Error("Run an interpretation first");
    }
    set({ isBacktesting: true, error: undefined });
    try {
      const result = await runBacktestRequest(state.strategy.id, state.strategy.strategySpec);
      set({ backtest: result });
      return result;
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Failed to run backtest" });
      throw error;
    } finally {
      set({ isBacktesting: false });
    }
  },
  async refreshAlerts() {
    const state = get();
    if (!state.strategy) return;
    const events = await fetchAlertsRequest(state.strategy.id);
    set({ alerts: events });
  },
  async toggleAlerts(enabled: boolean) {
    const state = get();
    if (!state.strategy) {
      throw new Error("No strategy to toggle");
    }
    set({ isTogglingAlerts: true });
    try {
      await toggleAlertsRequest(state.strategy.id, enabled);
      set({ alertsEnabled: enabled });
    } finally {
      set({ isTogglingAlerts: false });
    }
  },
}));
