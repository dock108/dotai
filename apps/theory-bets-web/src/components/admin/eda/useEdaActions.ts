"use client";

import { useCallback } from "react";
import {
  runAnalysis,
  buildModel,
  downloadAnalysisCsv,
  downloadMicroModelCsv,
  runWalkforward,
  type GeneratedFeature,
  type TargetDefinition,
  type TriggerDefinition,
  type ExposureControls,
  type CleaningOptions,
  type AnalysisResponse,
  type ModelBuildResponse,
  type MicroModelRow,
  type TheoryMetrics,
  type McSummary,
  type WalkforwardResponse,
} from "@/lib/api/sportsAdmin";

interface UseEdaActionsParams {
  leagueCode: string;
  generatedFeatures: GeneratedFeature[];
  targetDefinition: TargetDefinition;
  triggerDefinition: TriggerDefinition;
  exposureControls: ExposureControls;
  diagnosticMode: boolean;
  seasonsForScope: number[];
  phase: "all" | "out_conf" | "conf" | "postseason";
  recentDaysValue: number | undefined;
  team: string;
  player: string;
  homeSpreadMin: string;
  homeSpreadMax: string;
  cleaningOptions: CleaningOptions;
  setAnalysisResult: (r: AnalysisResponse | null) => void;
  setMicroRows: (r: MicroModelRow[] | null) => void;
  setTheoryMetrics: (r: TheoryMetrics | null) => void;
  setMcSummary: (r: McSummary | null) => void;
  setModelResult: (r: ModelBuildResponse | null) => void;
  setMicroRowsRef: (r: string | null) => void;
  setStatusMessage: (s: string | null) => void;
  setAnalysisError: (s: string | null) => void;
  setModelError: (s: string | null) => void;
  setAnalysisLoading: (b: boolean) => void;
  setAnalysisRunning: (b: boolean) => void;
  setModelLoading: (b: boolean) => void;
  setModelRunning: (b: boolean) => void;
  setCsvLoading: (b: boolean) => void;
  setMicroCsvLoading: (b: boolean) => void;
  setWfRunning: (b: boolean) => void;
  setWfError: (s: string | null) => void;
  setWfResult: (r: WalkforwardResponse | null) => void;
  wfTrainDays: number;
  wfTestDays: number;
  wfStepDays: number;
  microRows: MicroModelRow[] | null;
  theoryMetrics: TheoryMetrics | null;
}

export function useEdaActions(params: UseEdaActionsParams) {
  const {
    leagueCode,
    generatedFeatures,
    targetDefinition,
    triggerDefinition,
    exposureControls,
    diagnosticMode,
    seasonsForScope,
    phase,
    recentDaysValue,
    team,
    player,
    homeSpreadMin,
    homeSpreadMax,
    cleaningOptions,
    setAnalysisResult,
    setMicroRows,
    setTheoryMetrics,
    setMcSummary,
    setModelResult,
    setMicroRowsRef,
    setStatusMessage,
    setAnalysisError,
    setModelError,
    setAnalysisLoading,
    setAnalysisRunning,
    setModelLoading,
    setModelRunning,
    setCsvLoading,
    setMicroCsvLoading,
    setWfRunning,
    setWfError,
    setWfResult,
    wfTrainDays,
    wfTestDays,
    wfStepDays,
    microRows,
    theoryMetrics,
  } = params;

  const handleRunAnalysis = useCallback(async () => {
    setAnalysisLoading(true);
    setAnalysisRunning(true);
    setStatusMessage("Analyzing games… this can take a couple of minutes.");
    setAnalysisError(null);
    try {
      const res = await runAnalysis({
        league_code: leagueCode,
        features: generatedFeatures,
        target_definition: targetDefinition,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase,
        recent_days: recentDaysValue,
        team: team || undefined,
        player: player || undefined,
        home_spread_min: homeSpreadMin ? Number(homeSpreadMin) : undefined,
        home_spread_max: homeSpreadMax ? Number(homeSpreadMax) : undefined,
        cleaning: cleaningOptions,
      });
      setAnalysisResult(res);
      setMicroRows(res.micro_rows ?? null);
      setTheoryMetrics(res.theory_metrics ?? null);
      setModelResult(null);
      setMcSummary(null);
      setMicroRowsRef(null);
      setStatusMessage("Analysis complete.");
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err));
      setAnalysisResult(null);
      setMicroRows(null);
      setTheoryMetrics(null);
      setMcSummary(null);
      setStatusMessage("Analysis failed. Check inputs and try again.");
    } finally {
      setAnalysisLoading(false);
      setAnalysisRunning(false);
    }
  }, [leagueCode, generatedFeatures, targetDefinition, diagnosticMode, seasonsForScope, phase, recentDaysValue, team, player, homeSpreadMin, homeSpreadMax, cleaningOptions, setAnalysisLoading, setAnalysisRunning, setStatusMessage, setAnalysisError, setAnalysisResult, setMicroRows, setTheoryMetrics, setModelResult, setMcSummary, setMicroRowsRef]);

  const handleBuildModel = useCallback(async () => {
    setModelLoading(true);
    setModelRunning(true);
    setStatusMessage("Building model + running MC… this can take a couple of minutes.");
    setModelError(null);
    try {
      const res = await buildModel({
        league_code: leagueCode,
        features: generatedFeatures,
        target_definition: targetDefinition,
        trigger_definition: triggerDefinition,
        exposure_controls: exposureControls,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase,
        recent_days: recentDaysValue,
        team: team || undefined,
        player: player || undefined,
        home_spread_min: homeSpreadMin ? Number(homeSpreadMin) : undefined,
        home_spread_max: homeSpreadMax ? Number(homeSpreadMax) : undefined,
        cleaning: cleaningOptions,
      });
      setModelResult(res);
      setMicroRows(res.micro_rows ?? microRows);
      setTheoryMetrics(res.theory_metrics ?? theoryMetrics);
      setMcSummary(res.mc_summary ?? null);
      setMicroRowsRef(null);
      setStatusMessage("Model build complete.");
    } catch (err) {
      setModelError(err instanceof Error ? err.message : String(err));
      setModelResult(null);
      setMcSummary(null);
      setStatusMessage("Model build failed. Check inputs and try again.");
    } finally {
      setModelLoading(false);
      setModelRunning(false);
    }
  }, [leagueCode, generatedFeatures, targetDefinition, triggerDefinition, exposureControls, diagnosticMode, seasonsForScope, phase, recentDaysValue, team, player, homeSpreadMin, homeSpreadMax, cleaningOptions, microRows, theoryMetrics, setModelLoading, setModelRunning, setStatusMessage, setModelError, setModelResult, setMicroRows, setTheoryMetrics, setMcSummary, setMicroRowsRef]);

  const handleDownloadCsv = useCallback(async () => {
    if (!generatedFeatures.length) return;
    setCsvLoading(true);
    try {
      const res = await downloadAnalysisCsv({
        league_code: leagueCode,
        features: generatedFeatures,
        target_definition: targetDefinition,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase,
        recent_days: recentDaysValue,
        team: team || undefined,
        player: player || undefined,
        home_spread_min: homeSpreadMin ? Number(homeSpreadMin) : undefined,
        home_spread_max: homeSpreadMax ? Number(homeSpreadMax) : undefined,
        cleaning: cleaningOptions,
      });
      const url = URL.createObjectURL(res);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err));
    } finally {
      setCsvLoading(false);
    }
  }, [generatedFeatures, leagueCode, targetDefinition, diagnosticMode, seasonsForScope, phase, recentDaysValue, team, player, homeSpreadMin, homeSpreadMax, cleaningOptions, setCsvLoading, setAnalysisError]);

  const handleDownloadMicroCsv = useCallback(async () => {
    if (!generatedFeatures.length) return;
    setMicroCsvLoading(true);
    try {
      const res = await downloadMicroModelCsv({
        league_code: leagueCode,
        features: generatedFeatures,
        target_definition: targetDefinition,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase,
        recent_days: recentDaysValue,
        team: team || undefined,
        player: player || undefined,
        home_spread_min: homeSpreadMin ? Number(homeSpreadMin) : undefined,
        home_spread_max: homeSpreadMax ? Number(homeSpreadMax) : undefined,
        cleaning: cleaningOptions,
      });
      const url = URL.createObjectURL(res);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err));
    } finally {
      setMicroCsvLoading(false);
    }
  }, [generatedFeatures, leagueCode, targetDefinition, diagnosticMode, seasonsForScope, phase, recentDaysValue, team, player, homeSpreadMin, homeSpreadMax, cleaningOptions, setMicroCsvLoading, setAnalysisError]);

  const handleRunWalkforward = useCallback(async () => {
    setWfRunning(true);
    setWfError(null);
    setWfResult(null);
    try {
      const res = await runWalkforward({
        league_code: leagueCode,
        features: generatedFeatures,
        target_definition: targetDefinition,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase,
        recent_days: recentDaysValue,
        team: team || undefined,
        player: player || undefined,
        home_spread_min: homeSpreadMin ? Number(homeSpreadMin) : undefined,
        home_spread_max: homeSpreadMax ? Number(homeSpreadMax) : undefined,
        cleaning: cleaningOptions,
        window: { train_days: wfTrainDays, test_days: wfTestDays, step_days: wfStepDays },
      });
      setWfResult(res);
    } catch (err) {
      setWfError(err instanceof Error ? err.message : String(err));
    } finally {
      setWfRunning(false);
    }
  }, [leagueCode, generatedFeatures, targetDefinition, diagnosticMode, seasonsForScope, phase, recentDaysValue, team, player, homeSpreadMin, homeSpreadMax, cleaningOptions, wfTrainDays, wfTestDays, wfStepDays, setWfRunning, setWfError, setWfResult]);

  return {
    handleRunAnalysis,
    handleBuildModel,
    handleDownloadCsv,
    handleDownloadMicroCsv,
    handleRunWalkforward,
  };
}

