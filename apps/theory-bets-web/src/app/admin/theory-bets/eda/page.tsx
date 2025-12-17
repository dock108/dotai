"use client";

import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import styles from "./page.module.css";
import { AdminCard, LoadingState, ErrorState } from "@/components/admin";
import { SUPPORTED_LEAGUES, type LeagueCode } from "@/lib/constants/sports";
import { useEdaViewModel, type EdaFormState } from "@/components/admin/eda/useEdaViewModel";
import {
  fetchStatKeys,
  generateFeatures,
  runAnalysis,
  buildModel,
  downloadAnalysisCsv,
  downloadPreviewCsv,
  downloadMicroModelCsv,
  fetchDataQuality,
  fetchAnalysisRuns,
  fetchAnalysisRun,
  runWalkforward,
  type AvailableStatKeysResponse,
  type GeneratedFeature,
  type AnalysisResponse,
  type ModelBuildResponse,
  type CleaningOptions,
  type DataQualitySummary,
  type MicroModelRow,
  type TheoryMetrics,
  type McSummary,
  type TargetDefinition,
  type TriggerDefinition,
  type ExposureControls,
  type AnalysisRunSummary,
  type WalkforwardResponse,
} from "@/lib/api/sportsAdmin";
import { FeatureListPanel } from "@/components/admin/eda/FeatureListPanel";
import { ResultsSection } from "@/components/admin/eda/ResultsSection";
import { PipelineTabs } from "@/components/admin/eda/PipelineTabs";
import { SavedRunsCard } from "@/components/admin/eda/SavedRunsCard";
import { TheoryForm } from "@/components/admin/eda/TheoryForm";
import { ResultsHeader } from "@/components/admin/eda/ResultsHeader";
import { WalkforwardPanel } from "@/components/admin/eda/WalkforwardPanel";
import { PublishingReadinessCard } from "@/components/admin/eda/PublishingReadinessCard";

type FormState = EdaFormState & {
  seasonType: string;
  marketType: string;
  side: string;
  closingOnly: boolean;
  includePlayerStats: boolean;
  teamStatKeys: string[];
  playerStatKeys: string[];
};

const INITIAL_FORM: FormState = {
  leagueCode: "NBA",
  seasons: "",
  seasonScope: "full",
  recentDays: "30",
  phase: "all",
  team: "",
  player: "",
  homeSpreadMin: "",
  homeSpreadMax: "",
  seasonType: "",
  marketType: "",
  side: "",
  closingOnly: true,
  includePlayerStats: false,
  teamStatKeys: [],
  playerStatKeys: [],
};

export default function TheoryBetsEdaPage() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statKeys, setStatKeys] = useState<AvailableStatKeysResponse | null>(null);
  const [loadingStatKeys, setLoadingStatKeys] = useState(false);
  const [generatedFeatures, setGeneratedFeatures] = useState<GeneratedFeature[]>([]);
  const [selectedFeatureNames, setSelectedFeatureNames] = useState<Set<string>>(new Set());
  const [featureSummary, setFeatureSummary] = useState<string | null>(null);
  const [featureError, setFeatureError] = useState<string | null>(null);
  const [includeRestDays, setIncludeRestDays] = useState(false);
  const [includeRolling, setIncludeRolling] = useState(false);
  const [rollingWindow, setRollingWindow] = useState(5);
  const [diagnosticMode, setDiagnosticMode] = useState(false);
  const [targetDefinition, setTargetDefinition] = useState<TargetDefinition>({
    target_class: "stat",
    target_name: "combined_score",
    metric_type: "numeric",
    odds_required: false,
  });
  const [targetLocked, setTargetLocked] = useState(true);
  const [triggerDefinition, setTriggerDefinition] = useState<TriggerDefinition>({
    prob_threshold: 0.55,
    confidence_band: null,
    min_edge_vs_implied: null,
  });
  const [exposureControls, setExposureControls] = useState<ExposureControls>({
    max_bets_per_day: 5,
    max_bets_per_side_per_day: null,
    spread_abs_min: null,
    spread_abs_max: null,
  });
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [microRows, setMicroRows] = useState<MicroModelRow[] | null>(null);
  const [theoryMetrics, setTheoryMetrics] = useState<TheoryMetrics | null>(null);
  const [mcSummary, setMcSummary] = useState<McSummary | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [microCsvLoading, setMicroCsvLoading] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [modelRunning, setModelRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [dataQuality, setDataQuality] = useState<DataQualitySummary | null>(null);
  const [qualityError, setQualityError] = useState<string | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [dqSearch, setDqSearch] = useState("");
  const [dqHideZero, setDqHideZero] = useState(false);
  const [dqSortKey, setDqSortKey] = useState<"null_pct" | "non_numeric" | "name">("null_pct");
  const [dqSortDir, setDqSortDir] = useState<"asc" | "desc">("desc");
  const [modelResult, setModelResult] = useState<ModelBuildResponse | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  const [modelLoading, setModelLoading] = useState(false);
  const [cleaningOptions, setCleaningOptions] = useState<CleaningOptions>({
    drop_if_all_null: false,
    drop_if_any_null: false,
    drop_if_non_numeric: false,
    min_non_null_features: undefined,
  });
  const [theoryDraftEdits, setTheoryDraftEdits] = useState<Record<string, string>>({});
  const [theoryDraftStatus, setTheoryDraftStatus] = useState<Record<string, "draft" | "accepted" | "rejected">>({});
  const [savedRuns, setSavedRuns] = useState<AnalysisRunSummary[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [microRowsRef, setMicroRowsRef] = useState<string | null>(null);
  const [pipelineStep, setPipelineStep] = useState<
    "theory" | "cohort" | "evaluation" | "market" | "modeling" | "mc" | "walk" | "live"
  >("theory");
  const [wfRunning, setWfRunning] = useState(false);
  const [wfResult, setWfResult] = useState<WalkforwardResponse | null>(null);
  const [wfError, setWfError] = useState<string | null>(null);
  const [wfTrainDays, setWfTrainDays] = useState(180);
  const [wfTestDays, setWfTestDays] = useState(14);
  const [wfStepDays, setWfStepDays] = useState(7);

  const {
    parseSeasons,
    seasonsForScope,
    recentDaysValue,
    gamesLink,
    featureLeakageSummary,
    featurePolicyMessage,
    primarySignalDrivers,
    dataQualityRows,
  } = useEdaViewModel({
    form,
    generatedFeatures,
    analysisResult,
    modelResult,
    dataQuality,
    dqSearch,
    dqHideZero,
    dqSortKey,
    dqSortDir,
  });

  const downloadJson = useCallback((filename: string, data: any) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  }, []);

  const loadStatKeys = useCallback(async (leagueCode: string) => {
    setLoadingStatKeys(true);
    try {
      const keys = await fetchStatKeys(leagueCode);
      setStatKeys(keys);
    } catch (err) {
      console.error("Failed to load stat keys:", err);
      setStatKeys(null);
    } finally {
      setLoadingStatKeys(false);
    }
  }, []);

  useEffect(() => {
    loadStatKeys(form.leagueCode);
  }, [form.leagueCode, loadStatKeys]);

  useEffect(() => {
    const loadRuns = async () => {
      setRunsLoading(true);
      setRunsError(null);
      try {
        const data = await fetchAnalysisRuns();
        setSavedRuns(data);
      } catch (err) {
        setRunsError(err instanceof Error ? err.message : String(err));
      } finally {
        setRunsLoading(false);
      }
    };
    loadRuns();
  }, []);

  const handleLeagueChange = (newLeague: LeagueCode) => {
    setForm((prev) => ({ ...prev, leagueCode: newLeague, teamStatKeys: [], playerStatKeys: [] }));
    setGeneratedFeatures([]);
    setFeatureSummary(null);
    setFeatureError(null);
    setDataQuality(null);
    setQualityError(null);
    setQualityLoading(false);
  };

  const toggleStatKey = (type: "teamStatKeys" | "playerStatKeys", key: string) => {
    setForm((prev) => {
      const current = prev[type];
      const updated = current.includes(key) ? current.filter((k) => k !== key) : [...current, key];
      return { ...prev, [type]: updated };
    });
  };

  const selectAllStatKeys = (type: "teamStatKeys" | "playerStatKeys") => {
    const keys = type === "teamStatKeys" ? statKeys?.team_stat_keys : statKeys?.player_stat_keys;
    if (keys) {
      setForm((prev) => ({ ...prev, [type]: [...keys] }));
    }
  };

  const clearStatKeys = (type: "teamStatKeys" | "playerStatKeys") => {
    setForm((prev) => ({ ...prev, [type]: [] }));
  };

  const handleGenerateFeatures = async () => {
    if (!analysisResult) {
      setFeatureError("Run Analyze before adding explanatory features.");
      return;
    }
    setFeatureError(null);
    try {
      const res = await generateFeatures({
        league_code: form.leagueCode,
        raw_stats: form.teamStatKeys.length ? form.teamStatKeys : statKeys?.team_stat_keys || [],
        include_rest_days: includeRestDays,
        include_rolling: includeRolling,
        rolling_window: rollingWindow || 5,
      });
      setGeneratedFeatures(res.features);
      setSelectedFeatureNames((prev) => {
        const nextNames = new Set(res.features.map((f) => f.name));
        return new Set(Array.from(prev).filter((n) => nextNames.has(n)));
      });
      setFeatureSummary(res.summary);
    } catch (err) {
      setFeatureError(err instanceof Error ? err.message : String(err));
      setGeneratedFeatures([]);
      setSelectedFeatureNames(new Set());
      setFeatureSummary(null);
    }
  };

  const selectedFeatures = generatedFeatures.filter((f) => selectedFeatureNames.has(f.name));
  const canAddFeatures = Boolean(analysisResult);

  const toggleFeature = useCallback((name: string) => {
    setSelectedFeatureNames((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const selectAllFeatures = useCallback(() => {
    setSelectedFeatureNames(new Set(generatedFeatures.map((f) => f.name)));
  }, [generatedFeatures]);

  const selectNoFeatures = useCallback(() => {
    setSelectedFeatureNames(new Set());
  }, []);

  const selectByCategory = useCallback(
    (category: string) => {
      setSelectedFeatureNames(new Set(generatedFeatures.filter((f) => f.category === category).map((f) => f.name)));
    },
    [generatedFeatures]
  );

  const handleRunAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysisRunning(true);
    setStatusMessage("Analyzing games… this can take a couple of minutes.");
    setAnalysisError(null);
    try {
      const res = await runAnalysis({
        league_code: form.leagueCode,
        features: selectedFeatures,
        target_definition: targetDefinition,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase: form.phase,
        recent_days: recentDaysValue,
        team: form.team || undefined,
        player: form.player || undefined,
        home_spread_min: form.homeSpreadMin ? Number(form.homeSpreadMin) : undefined,
        home_spread_max: form.homeSpreadMax ? Number(form.homeSpreadMax) : undefined,
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
  };

  const handleBuildModel = async () => {
    if (selectedFeatures.length === 0) {
      setModelError("Select at least one feature before building a model.");
      return;
    }
    setModelLoading(true);
    setModelRunning(true);
    setStatusMessage("Building model + running MC… this can take a couple of minutes.");
    setModelError(null);
    try {
      const res = await buildModel({
        league_code: form.leagueCode,
        features: selectedFeatures,
        target_definition: targetDefinition,
        trigger_definition: triggerDefinition,
        exposure_controls: exposureControls,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase: form.phase,
        recent_days: recentDaysValue,
        team: form.team || undefined,
        player: form.player || undefined,
        home_spread_min: form.homeSpreadMin ? Number(form.homeSpreadMin) : undefined,
        home_spread_max: form.homeSpreadMax ? Number(form.homeSpreadMax) : undefined,
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
  };

  const handleDownloadCsv = async () => {
    if (!generatedFeatures.length) return;
    setCsvLoading(true);
    try {
      if (selectedFeatures.length === 0) {
        setAnalysisError("Select at least one feature before exporting CSV.");
        return;
      }
      const res = await downloadAnalysisCsv({
        league_code: form.leagueCode,
        features: selectedFeatures,
        target_definition: targetDefinition,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase: form.phase,
        recent_days: recentDaysValue,
        team: form.team || undefined,
        player: form.player || undefined,
        home_spread_min: form.homeSpreadMin ? Number(form.homeSpreadMin) : undefined,
        home_spread_max: form.homeSpreadMax ? Number(form.homeSpreadMax) : undefined,
        cleaning: cleaningOptions,
      });
      const url = URL.createObjectURL(res);
      const tab = window.open(url, "_blank");
      if (!tab) throw new Error("Popup blocked.");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err));
    } finally {
      setCsvLoading(false);
    }
  };

  const handleDownloadMicroCsv = async () => {
    if (!generatedFeatures.length) return;
    setMicroCsvLoading(true);
    try {
      if (selectedFeatures.length === 0) {
        setAnalysisError("Select at least one feature before exporting micro CSV.");
        return;
      }
      const res = await downloadMicroModelCsv({
        league_code: form.leagueCode,
        features: selectedFeatures,
        target_definition: targetDefinition,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase: form.phase,
        recent_days: recentDaysValue,
        team: form.team || undefined,
        player: form.player || undefined,
        home_spread_min: form.homeSpreadMin ? Number(form.homeSpreadMin) : undefined,
        home_spread_max: form.homeSpreadMax ? Number(form.homeSpreadMax) : undefined,
        cleaning: cleaningOptions,
      });
      const url = URL.createObjectURL(res);
      const tab = window.open(url, "_blank");
      if (!tab) throw new Error("Popup blocked.");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err));
    } finally {
      setMicroCsvLoading(false);
    }
  };

  const handleDownloadMicroJson = () => {
    if (microRows) downloadJson("micro_rows.json", microRows);
  };

  const handleRunWalkforward = async () => {
    setWfRunning(true);
    setWfError(null);
    setWfResult(null);
    try {
      if (selectedFeatures.length === 0) {
        setWfError("Select at least one feature before running walk-forward.");
        setWfRunning(false);
        return;
      }
      const res = await runWalkforward({
        league_code: form.leagueCode,
        features: selectedFeatures,
        target_definition: targetDefinition,
        context: diagnosticMode ? "diagnostic" : "deployable",
        seasons: seasonsForScope,
        phase: form.phase,
        recent_days: recentDaysValue,
        team: form.team || undefined,
        player: form.player || undefined,
        home_spread_min: form.homeSpreadMin ? Number(form.homeSpreadMin) : undefined,
        home_spread_max: form.homeSpreadMax ? Number(form.homeSpreadMax) : undefined,
        cleaning: cleaningOptions,
        window: { train_days: wfTrainDays, test_days: wfTestDays, step_days: wfStepDays },
      });
      setWfResult(res);
    } catch (err) {
      setWfError(err instanceof Error ? err.message : String(err));
    } finally {
      setWfRunning(false);
    }
  };

  const handleRefreshRuns = async () => {
    setRunsLoading(true);
    setRunsError(null);
    try {
      const data = await fetchAnalysisRuns();
      setSavedRuns(data);
    } catch (err) {
      setRunsError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunsLoading(false);
    }
  };

  const handleOpenRun = async (runId: string) => {
    try {
      const detail = await fetchAnalysisRun(runId);
      const evaluation = detail.evaluation as any;
      const mrs = (detail.micro_rows_sample as any) ?? null;
      const analysis: AnalysisResponse = {
        sample_size: detail.cohort_size ?? (mrs ? mrs.length : 0),
        baseline_value: evaluation?.baseline_value ?? 0,
        correlations: [],
        best_segments: [],
        insights: [],
        cleaning_summary: null,
        micro_rows: mrs,
        theory_metrics: null,
        evaluation: evaluation ?? null,
        meta: null,
        theory: detail.target as any ?? null,
        cohort: null,
        modeling: detail.modeling as any ?? null,
        monte_carlo: detail.monte_carlo as any ?? null,
        notes: null,
        feature_policy: null,
        run_id: runId,
      };
      setAnalysisResult(analysis);
      setMicroRows(mrs ?? null);
      setTheoryMetrics(null);
      setMcSummary((detail.mc_summary as any) ?? null);
      setMicroRowsRef(detail.micro_rows_ref ?? null);
      if (detail.target?.target_class && detail.target?.target_name) {
        setTargetDefinition((prev) => ({ ...prev, target_class: detail.target!.target_class, target_name: detail.target!.target_name }));
      }
    } catch (err) {
      setRunsError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleReset = () => {
    setForm(INITIAL_FORM);
    setGeneratedFeatures([]);
    setFeatureSummary(null);
    setFeatureError(null);
    setDiagnosticMode(false);
    setTargetDefinition({ target_class: "stat", target_name: "combined_score", metric_type: "numeric", odds_required: false });
    setTargetLocked(true);
    setTriggerDefinition({ prob_threshold: 0.55, confidence_band: null, min_edge_vs_implied: null });
    setExposureControls({ max_bets_per_day: 5, max_bets_per_side_per_day: null, spread_abs_min: null, spread_abs_max: null });
    setAnalysisResult(null);
    setAnalysisError(null);
    setMicroRows(null);
    setTheoryMetrics(null);
    setMcSummary(null);
    setModelResult(null);
    setModelError(null);
    setError(null);
    setDataQuality(null);
    setQualityError(null);
    setCleaningOptions({ drop_if_all_null: false, drop_if_any_null: false, drop_if_non_numeric: false, min_non_null_features: undefined });
    setTheoryDraftEdits({});
    setTheoryDraftStatus({});
  };

  const mcStatus = (modelResult?.monte_carlo as any) ?? (analysisResult as any)?.monte_carlo ?? null;
  const mcAvailable = mcStatus?.available ?? false;
  const mcReason = mcStatus?.reason_not_available ?? mcStatus?.reason_not_run ?? null;
  const isStatTarget = targetDefinition.target_class === "stat";
  const anyAccepted = Object.values(theoryDraftStatus).some((s) => s === "accepted");
  const evaluation = (analysisResult?.evaluation ?? modelResult?.evaluation ?? null) as any;

  if (loading) return <LoadingState message="Loading EDA workspace..." />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>EDA &amp; Modeling Lab</h1>
        <p className={styles.subtitle}>
          Feature engineering, correlation analysis, model training, Monte Carlo robustness, walk-forward replay.{" "}
          <Link href="/admin/theory-bets">← Back</Link>
        </p>
      </header>

      <PipelineTabs step={pipelineStep} onChange={(id) => setPipelineStep(id)} />

      <AdminCard>
        <form onSubmit={(e) => e.preventDefault()}>
          <div className={styles.formGrid}>
            {/* Saved runs */}
            <div className={styles.fieldFull}>
              <SavedRunsCard
                savedRuns={savedRuns}
                runsLoading={runsLoading}
                runsError={runsError}
                onRefresh={handleRefreshRuns}
                onOpenLatest={() => savedRuns[0] && handleOpenRun(savedRuns[0].run_id)}
                onOpenRun={handleOpenRun}
              />
            </div>

            {/* Theory summary */}
            <div className={styles.fieldFull}>
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Theory definition (summary)</h4>
                <div className={styles.metricsGrid}>
                  <div>Target class: <span className={styles.summaryValue}>{targetDefinition.target_class}</span></div>
                  <div>Target: <span className={styles.summaryValue}>{targetDefinition.target_name}</span></div>
                  <div>Filters: <span className={styles.summaryValue}>{form.seasons || "all seasons"} · phase {form.phase}</span></div>
                  <div>Team: <span className={styles.summaryValue}>{form.team || "any"}</span> · Player: <span className={styles.summaryValue}>{form.player || "any"}</span></div>
                  </div>
            </div>
          </div>

            {/* Form fields for theory definition */}
            <TheoryForm
              form={form}
              setForm={setForm}
              pipelineStep={pipelineStep}
              statKeys={statKeys}
              loadingStatKeys={loadingStatKeys}
              toggleStatKey={toggleStatKey}
              selectAllStatKeys={selectAllStatKeys}
              clearStatKeys={clearStatKeys}
              handleLeagueChange={handleLeagueChange}
              targetDefinition={targetDefinition}
              setTargetDefinition={setTargetDefinition}
              targetLocked={targetLocked}
              setTargetLocked={setTargetLocked}
              triggerDefinition={triggerDefinition}
              setTriggerDefinition={setTriggerDefinition}
              exposureControls={exposureControls}
              setExposureControls={setExposureControls}
              diagnosticMode={diagnosticMode}
              setDiagnosticMode={setDiagnosticMode}
              includeRestDays={includeRestDays}
              setIncludeRestDays={setIncludeRestDays}
              includeRolling={includeRolling}
              setIncludeRolling={setIncludeRolling}
              rollingWindow={rollingWindow}
              setRollingWindow={setRollingWindow}
              generatedFeatures={generatedFeatures}
              featureSummary={featureSummary}
              featureError={featureError}
              onGenerateFeatures={handleGenerateFeatures}
              onRunAnalysis={handleRunAnalysis}
              onBuildModel={handleBuildModel}
              analysisRunning={analysisRunning}
              modelRunning={modelRunning}
              isStatTarget={isStatTarget}
              mcAvailable={mcAvailable}
              mcReason={mcReason}
              canAddFeatures={canAddFeatures}
              selectedFeatureCount={selectedFeatures.length}
            />

            {/* Feature list panel */}
          {analysisResult && (
            <FeatureListPanel
              features={generatedFeatures}
              selectedFeatureNames={selectedFeatureNames}
              onToggleFeature={toggleFeature}
              onSelectAll={selectAllFeatures}
              onSelectNone={selectNoFeatures}
              onSelectByCategory={selectByCategory}
              featureSummary={featureSummary}
              featureError={featureError}
              featureLeakageSummary={featureLeakageSummary}
              featurePolicyMessage={featurePolicyMessage}
            />
          )}

            {/* Results header with status/downloads */}
            {analysisResult && (
              <div className={styles.fieldFull}>
                <ResultsHeader
                  analysisResult={analysisResult}
                  targetDefinition={targetDefinition}
                  evaluation={evaluation}
                  statusMessage={statusMessage}
                  gamesLink={gamesLink}
                  isStatTarget={isStatTarget}
                  csvLoading={csvLoading}
                  microCsvLoading={microCsvLoading}
                  onDownloadAnalysisCsv={handleDownloadCsv}
                  onDownloadMicroCsv={handleDownloadMicroCsv}
                  onDownloadMicroJson={handleDownloadMicroJson}
                  microRowsRef={microRowsRef}
                />
                  </div>
            )}

            {/* Main results for cohort/eval/market/modeling/mc panels */}
            {(pipelineStep === "cohort" || pipelineStep === "evaluation" || pipelineStep === "market" || pipelineStep === "modeling" || pipelineStep === "mc") && (
            <ResultsSection
              analysisResult={analysisResult}
              microRows={microRows}
              theoryMetrics={theoryMetrics}
              modelResult={modelResult}
              primarySignalDrivers={primarySignalDrivers}
              gamesLink={gamesLink}
              microCsvLoading={microCsvLoading}
              csvLoading={csvLoading}
              onDownloadMicroCsv={handleDownloadMicroCsv}
              onDownloadCsv={handleDownloadCsv}
              mcSummary={mcSummary}
              theoryDraftEdits={theoryDraftEdits}
              theoryDraftStatus={theoryDraftStatus}
              setTheoryDraftEdits={setTheoryDraftEdits}
              setTheoryDraftStatus={setTheoryDraftStatus}
              downloadJson={downloadJson}
            />
            )}

            {/* Walk-forward panel */}
            {pipelineStep === "walk" && (
              <div className={styles.fieldFull}>
                <WalkforwardPanel
                  wfTrainDays={wfTrainDays}
                  wfTestDays={wfTestDays}
                  wfStepDays={wfStepDays}
                  setWfTrainDays={setWfTrainDays}
                  setWfTestDays={setWfTestDays}
                  setWfStepDays={setWfStepDays}
                  wfRunning={wfRunning}
                  isStatTarget={isStatTarget}
                  generatedFeaturesLength={generatedFeatures.length}
                  wfError={wfError}
                  wfResult={wfResult}
                  onRun={handleRunWalkforward}
                />
                    </div>
                  )}

            {/* Live matches stub */}
            {pipelineStep === "live" && (
              <div className={styles.fieldFull}>
                    <div className={styles.sectionCard}>
                  <h4 className={styles.sectionTitle}>Live matches (stub)</h4>
                  <p className={styles.hint}>Future: hook to live/incoming games for the selected league with model/trigger overlay.</p>
                        </div>
                          </div>
                        )}

            {/* Publishing readiness card */}
            {modelResult && (
              <div className={styles.fieldFull}>
                <PublishingReadinessCard
                  modelResult={modelResult}
                  diagnosticMode={diagnosticMode}
                  hasPostGameLeakage={featureLeakageSummary.hasPostGame}
                  anyAccepted={anyAccepted}
                  theoryDraftStatus={theoryDraftStatus}
                  theoryDraftEdits={theoryDraftEdits}
                  setTheoryDraftStatus={setTheoryDraftStatus}
                  setTheoryDraftEdits={setTheoryDraftEdits}
                />
                </div>
              )}

            {/* Reset button */}
            <div className={styles.fieldFull}>
            <div className={styles.actions}>
              <button type="button" className={styles.secondaryButton} onClick={handleReset}>
                Reset
              </button>
              </div>
            </div>
          </div>
        </form>
      </AdminCard>
    </div>
  );
}
