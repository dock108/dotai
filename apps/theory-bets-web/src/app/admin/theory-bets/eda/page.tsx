"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, useCallback } from "react";
import styles from "./page.module.css";
import { AdminCard, LoadingState, ErrorState } from "@/components/admin";
import { SUPPORTED_LEAGUES, type LeagueCode } from "@/lib/constants/sports";
import {
  fetchStatKeys,
  generateFeatures,
  runAnalysis,
  buildModel,
  downloadAnalysisCsv,
  downloadPreviewCsv,
  downloadMicroModelCsv,
  fetchDataQuality,
  type AvailableStatKeysResponse,
  type GeneratedFeature,
  type AnalysisResponse,
  type ModelBuildResponse,
  type CleaningOptions,
  type DataQualitySummary,
  type MicroModelRow,
  type TheoryMetrics,
  type McSummary,
} from "@/lib/api/sportsAdmin";

type FormState = {
  leagueCode: LeagueCode;
  seasons: string; // comma-separated seasons for UI; parsed before requests
  seasonScope: "full" | "current" | "recent";
  recentDays: string;
  phase: "all" | "out_conf" | "conf" | "postseason";
  team: string;
  player: string;
  homeSpreadMin: string;
  homeSpreadMax: string;
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
  const [featureSummary, setFeatureSummary] = useState<string | null>(null);
  const [featureError, setFeatureError] = useState<string | null>(null);
  const [includeRestDays, setIncludeRestDays] = useState(false);
  const [includeRolling, setIncludeRolling] = useState(false);
  const [rollingWindow, setRollingWindow] = useState(5);
  const [analysisTarget, setAnalysisTarget] = useState<"cover" | "win" | "over">("cover");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [microRows, setMicroRows] = useState<MicroModelRow[] | null>(null);
  const [theoryMetrics, setTheoryMetrics] = useState<TheoryMetrics | null>(null);
  const [mcSummary, setMcSummary] = useState<McSummary | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [microCsvLoading, setMicroCsvLoading] = useState(false);
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

  const gamesLink = useMemo(() => {
    const params = new URLSearchParams();
    params.set("league", form.leagueCode);
    if (form.seasons.trim()) params.set("seasons", form.seasons.trim());
    if (form.team.trim()) params.set("team", form.team.trim());
    if (form.player.trim()) params.set("player", form.player.trim());
    const qs = params.toString();
    return `/admin/theory-bets/games${qs ? `?${qs}` : ""}`;
  }, [form.leagueCode, form.seasons, form.team, form.player]);

  // Fetch available stat keys when league changes
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

  const handleLeagueChange = (newLeague: LeagueCode) => {
    setForm((prev) => ({
      ...prev,
      leagueCode: newLeague,
      teamStatKeys: [],
      playerStatKeys: [],
    }));
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
      const updated = current.includes(key)
        ? current.filter((k) => k !== key)
        : [...current, key];
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

  const parseSeasons = useCallback((): number[] | undefined => {
    if (!form.seasons.trim()) return undefined;
    const nums = form.seasons
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => Number(s))
      .filter((n) => !Number.isNaN(n));
    return nums.length ? nums : undefined;
  }, [form.seasons]);

  const seasonsForScope = useMemo(() => {
    const parsed = parseSeasons();
    if (!parsed) return undefined;
    if (form.seasonScope === "current") {
      return [Math.max(...parsed)];
    }
    return parsed;
  }, [form.seasonScope, parseSeasons]);

  const recentDaysValue = useMemo(() => {
    if (form.seasonScope !== "recent") return undefined;
    const n = Number(form.recentDays);
    return Number.isFinite(n) && n > 0 ? n : undefined;
  }, [form.seasonScope, form.recentDays]);

  const handleGenerateFeatures = async () => {
    setFeatureError(null);
    setAnalysisResult(null);
    setMicroRows(null);
    setTheoryMetrics(null);
    setMcSummary(null);
    setAnalysisError(null);
    setDataQuality(null);
    setQualityError(null);
    setQualityLoading(false);
    setDqSearch("");
    setDqHideZero(false);
    setDqSortKey("null_pct");
    setDqSortDir("desc");
    try {
      const res = await generateFeatures({
        league_code: form.leagueCode,
        raw_stats: form.teamStatKeys.length ? form.teamStatKeys : statKeys?.team_stat_keys || [],
        include_rest_days: includeRestDays,
        include_rolling: includeRolling,
        rolling_window: rollingWindow || 5,
      });
      setGeneratedFeatures(res.features);
      setFeatureSummary(res.summary);
    } catch (err) {
      setFeatureError(err instanceof Error ? err.message : String(err));
      setGeneratedFeatures([]);
      setFeatureSummary(null);
    }
  };

  const handleRunAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const res = await runAnalysis({
        league_code: form.leagueCode,
        features: generatedFeatures,
        target: analysisTarget,
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
       setMicroRows(res.micro_model_results ?? null);
       setTheoryMetrics(res.theory_metrics ?? null);
      setModelResult(null);
      setMcSummary(null);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err));
      setAnalysisResult(null);
      setMicroRows(null);
      setTheoryMetrics(null);
      setMcSummary(null);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handlePreviewCsv = async () => {
    if (!generatedFeatures.length) return;
    setQualityError(null);
    try {
      const res = await downloadPreviewCsv({
        league_code: form.leagueCode,
        features: generatedFeatures,
        seasons: seasonsForScope,
        phase: form.phase,
        recent_days: recentDaysValue,
        target: analysisTarget,
        team: form.team || undefined,
        player: form.player || undefined,
        home_spread_min: form.homeSpreadMin ? Number(form.homeSpreadMin) : undefined,
        home_spread_max: form.homeSpreadMax ? Number(form.homeSpreadMax) : undefined,
        include_target: true,
      });
      const url = URL.createObjectURL(res);
      const tab = window.open(url, "_blank");
      if (!tab) {
        throw new Error("Popup blocked. Please allow popups for this site.");
      }
      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 60_000);
    } catch (err) {
      setQualityError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleLoadDataQuality = async () => {
    if (!generatedFeatures.length) return;
    setQualityLoading(true);
    setQualityError(null);
    try {
      const summary = await fetchDataQuality({
        league_code: form.leagueCode,
        features: generatedFeatures,
        seasons: seasonsForScope,
        phase: form.phase,
        recent_days: recentDaysValue,
        team: form.team || undefined,
        player: form.player || undefined,
        home_spread_min: form.homeSpreadMin ? Number(form.homeSpreadMin) : undefined,
        home_spread_max: form.homeSpreadMax ? Number(form.homeSpreadMax) : undefined,
        sort_by: dqSortKey,
        sort_dir: dqSortDir,
      });
      setDataQuality(summary);
    } catch (err) {
      setQualityError(err instanceof Error ? err.message : String(err));
      setDataQuality(null);
    } finally {
      setQualityLoading(false);
    }
  };

  const handleDownloadCsv = async () => {
    if (!generatedFeatures.length) return;
    setCsvLoading(true);
    try {
      const res = await downloadAnalysisCsv({
        league_code: form.leagueCode,
        features: generatedFeatures,
        target: analysisTarget,
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
      if (!tab) {
        throw new Error("Popup blocked. Please allow popups for this site.");
      }
      // Cleanup after some time
      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 60_000);
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
      const res = await downloadMicroModelCsv({
        league_code: form.leagueCode,
        features: generatedFeatures,
        target: analysisTarget,
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
      if (!tab) {
        throw new Error("Popup blocked. Please allow popups for this site.");
      }
      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 60_000);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err));
    } finally {
      setMicroCsvLoading(false);
    }
  };

  const handleBuildModel = async () => {
    setModelLoading(true);
    setModelError(null);
    try {
      const res = await buildModel({
        league_code: form.leagueCode,
        features: generatedFeatures,
        target: analysisTarget,
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
      setMicroRows(res.micro_model_results ?? microRows);
      setTheoryMetrics(res.theory_metrics ?? theoryMetrics);
      setMcSummary(res.mc_summary ?? null);
    } catch (err) {
      setModelError(err instanceof Error ? err.message : String(err));
      setModelResult(null);
      setMcSummary(null);
    } finally {
      setModelLoading(false);
    }
  };

  const handleReset = () => {
    setForm(INITIAL_FORM);
    setGeneratedFeatures([]);
    setFeatureSummary(null);
    setFeatureError(null);
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
    setDqSearch("");
    setDqHideZero(false);
    setDqSortKey("null_pct");
    setDqSortDir("desc");
    setCleaningOptions({
      drop_if_all_null: false,
      drop_if_any_null: false,
      drop_if_non_numeric: false,
      min_non_null_features: undefined,
    });
  };

  const dataQualityRows = useMemo(() => {
    if (!dataQuality) return [];
    const entries = Object.entries(dataQuality.feature_stats).map(([name, stats]) => ({
      name,
      ...stats,
    }));
    let rows = entries;
    if (dqSearch.trim()) {
      const needle = dqSearch.toLowerCase();
      rows = rows.filter((r) => r.name.toLowerCase().includes(needle));
    }
    if (dqHideZero) {
      rows = rows.filter((r) => r.nulls > 0 || r.non_numeric > 0);
    }
    rows = [...rows].sort((a, b) => {
      const dir = dqSortDir === "asc" ? 1 : -1;
      if (dqSortKey === "name") return a.name.localeCompare(b.name) * dir;
      if (dqSortKey === "non_numeric") return (a.non_numeric - b.non_numeric) * dir;
      return (a.null_pct - b.null_pct) * dir;
    });
    return rows;
  }, [dataQuality, dqSearch, dqHideZero, dqSortKey, dqSortDir]);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>EDA & Modeling Lab</h1>
        <p className={styles.subtitle}>
          Internal explorer for building matchup features, targets, and intuition before wiring into the theory engine.
        </p>
      </header>

      <AdminCard>
        <form onSubmit={(e) => e.preventDefault()}>
          <div className={styles.formGrid}>
            <div className={styles.field}>
              <label className={styles.label}>League</label>
              <select
                className={styles.select}
                value={form.leagueCode}
                onChange={(e) => handleLeagueChange(e.target.value as LeagueCode)}
              >
                {SUPPORTED_LEAGUES.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Seasons (comma separated)</label>
              <input
                className={styles.input}
                type="text"
                value={form.seasons}
                onChange={(e) => setForm((prev) => ({ ...prev, seasons: e.target.value }))}
                placeholder="2023, 2024"
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Season scope</label>
              <select
                className={styles.select}
                value={form.seasonScope}
                onChange={(e) => setForm((prev) => ({ ...prev, seasonScope: e.target.value as FormState["seasonScope"] }))}
              >
                <option value="full">Full season (all selected seasons)</option>
                <option value="current">Current season (latest selected)</option>
                <option value="recent">Recent window (days)</option>
              </select>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Recent days</label>
              <input
                className={styles.input}
                type="number"
                min={1}
                max={365}
                value={form.recentDays}
                onChange={(e) => setForm((prev) => ({ ...prev, recentDays: e.target.value }))}
                disabled={form.seasonScope !== "recent"}
              />
              <p className={styles.hint}>Used only when scope = Recent.</p>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Phase (NCAAB)</label>
              <select
                className={styles.select}
                value={form.phase}
                onChange={(e) => setForm((prev) => ({ ...prev, phase: e.target.value as FormState["phase"] }))}
              >
                <option value="all">All</option>
                <option value="out_conf">Out of conference (before 01/01)</option>
                <option value="conf">Conference (01/01 – 03/15)</option>
                <option value="postseason">Postseason (03/16+)</option>
              </select>
              <p className={styles.hint}>Applied only for NCAAB; ignored for other leagues.</p>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Team filter (optional)</label>
              <input
                className={styles.input}
                type="text"
                placeholder="Team name / short name / abbreviation"
                value={form.team}
                onChange={(e) => setForm((prev) => ({ ...prev, team: e.target.value }))}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Player filter (optional)</label>
              <input
                className={styles.input}
                type="text"
                placeholder="Player name substring"
                value={form.player}
                onChange={(e) => setForm((prev) => ({ ...prev, player: e.target.value }))}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Season type (optional)</label>
              <input
                className={styles.input}
                type="text"
                placeholder="regular, playoffs, tournament..."
                value={form.seasonType}
                onChange={(e) => setForm((prev) => ({ ...prev, seasonType: e.target.value }))}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Market type (optional)</label>
              <select
                className={styles.select}
                value={form.marketType}
                onChange={(e) => setForm((prev) => ({ ...prev, marketType: e.target.value }))}
              >
                <option value="">Any</option>
                <option value="spread">Spread</option>
                <option value="total">Total</option>
                <option value="moneyline">Moneyline</option>
              </select>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Side (optional)</label>
              <select
                className={styles.select}
                value={form.side}
                onChange={(e) => setForm((prev) => ({ ...prev, side: e.target.value }))}
              >
                <option value="">Any</option>
                <option value="home">Home</option>
                <option value="away">Away</option>
                <option value="over">Over</option>
                <option value="under">Under</option>
              </select>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Home spread min</label>
              <input
                className={styles.input}
                type="number"
                value={form.homeSpreadMin}
                onChange={(e) => setForm((prev) => ({ ...prev, homeSpreadMin: e.target.value }))}
                placeholder="0"
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Home spread max</label>
              <input
                className={styles.input}
                type="number"
                value={form.homeSpreadMax}
                onChange={(e) => setForm((prev) => ({ ...prev, homeSpreadMax: e.target.value }))}
                placeholder="9.5"
              />
            </div>

            <div className={styles.fieldFull}>
              <label className={styles.label}>
                Team stat keys
                {loadingStatKeys && <span className={styles.loadingBadge}>Loading...</span>}
                {!loadingStatKeys && statKeys && (
                  <span className={styles.countBadge}>
                    {form.teamStatKeys.length}/{statKeys.team_stat_keys.length} selected
                  </span>
                )}
              </label>
              {statKeys && statKeys.team_stat_keys.length > 0 ? (
                <>
                  <div className={styles.statKeyActions}>
                    <button type="button" className={styles.linkButton} onClick={() => selectAllStatKeys("teamStatKeys")}>
                      Select all
                    </button>
                    <button type="button" className={styles.linkButton} onClick={() => clearStatKeys("teamStatKeys")}>
                      Clear
                    </button>
                  </div>
                  <div className={styles.checkboxGrid}>
                    {statKeys.team_stat_keys.map((key) => (
                      <label key={key} className={styles.checkboxLabel}>
                        <input
                          type="checkbox"
                          checked={form.teamStatKeys.includes(key)}
                          onChange={() => toggleStatKey("teamStatKeys", key)}
                        />
                        <span className={styles.checkboxText}>{key}</span>
                      </label>
                    ))}
                  </div>
                </>
              ) : (
                <p className={styles.hint}>
                  {loadingStatKeys ? "Loading available stats..." : "No team stats found for this league."}
                </p>
              )}
              <p className={styles.hint}>Leave empty to include all team stats in results.</p>
            </div>

            <div className={styles.fieldFull}>
              <label className={styles.label}>
                Player stat keys
                {loadingStatKeys && <span className={styles.loadingBadge}>Loading...</span>}
                {!loadingStatKeys && statKeys && (
                  <span className={styles.countBadge}>
                    {form.playerStatKeys.length}/{statKeys.player_stat_keys.length} selected
                  </span>
                )}
              </label>
              {statKeys && statKeys.player_stat_keys.length > 0 ? (
                <>
                  <div className={styles.statKeyActions}>
                    <button type="button" className={styles.linkButton} onClick={() => selectAllStatKeys("playerStatKeys")}>
                      Select all
                    </button>
                    <button type="button" className={styles.linkButton} onClick={() => clearStatKeys("playerStatKeys")}>
                      Clear
                    </button>
                  </div>
                  <div className={styles.checkboxGrid}>
                    {statKeys.player_stat_keys.map((key) => (
                      <label key={key} className={styles.checkboxLabel}>
                        <input
                          type="checkbox"
                          checked={form.playerStatKeys.includes(key)}
                          onChange={() => toggleStatKey("playerStatKeys", key)}
                        />
                        <span className={styles.checkboxText}>{key}</span>
                      </label>
                    ))}
                  </div>
                </>
              ) : (
                <p className={styles.hint}>
                  {loadingStatKeys ? "Loading available stats..." : "No player stats found for this league."}
                </p>
              )}
              <p className={styles.hint}>Only used when &quot;Include player-level stats&quot; is checked.</p>
            </div>
          </div>

          <div className={styles.filterSummary}>
            <strong>Applied filters:</strong>{" "}
            {seasonsForScope?.join(", ") || "All seasons"} · Scope: {form.seasonScope}
            {form.seasonScope === "recent" && recentDaysValue ? ` (${recentDaysValue}d)` : ""} ·{" "}
            {form.homeSpreadMin || form.homeSpreadMax
              ? `Home spread ${form.homeSpreadMin || "-"} to ${form.homeSpreadMax || "-"}`
              : "No spread band"}{" "}
            · Phase: {form.phase} · {form.team ? `Team: ${form.team}` : "Team: any"} ·{" "}
            {form.player ? `Player: ${form.player}` : "Player: any"}
          </div>

          <div className={styles.featureSection}>
            <div className={styles.featureHeader}>
              <h3 className={styles.sectionTitle}>Workflow</h3>
              <p className={styles.hint}>Generate → Analyze → Review micro/metrics → Build model → MC.</p>
            </div>

            <div className={styles.contextRow}>
              <label className={styles.toggle}>
                <input type="checkbox" checked={includeRestDays} onChange={(e) => setIncludeRestDays(e.target.checked)} />
                Include rest days
              </label>
              <label className={styles.toggle}>
                <input type="checkbox" checked={includeRolling} onChange={(e) => setIncludeRolling(e.target.checked)} />
                Include rolling averages
              </label>
              {includeRolling && (
                <label className={styles.inlineField}>
                  Window
                  <input
                    type="number"
                    min={2}
                    max={15}
                    className={styles.inputInline}
                    value={rollingWindow}
                    onChange={(e) => setRollingWindow(Number(e.target.value) || 5)}
                  />
                </label>
              )}
              <button type="button" className={styles.primaryButton} onClick={handleGenerateFeatures}>
                Generate features
              </button>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={handleRunAnalysis}
                disabled={analysisLoading || generatedFeatures.length === 0}
              >
                {analysisLoading ? "Running analysis..." : "Analyze"}
              </button>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={handleBuildModel}
                disabled={modelLoading || !analysisResult}
              >
                {modelLoading ? "Building model..." : "Build model / MC"}
              </button>
            </div>

            {featureError && <div className={styles.error}>{featureError}</div>}
            {featureSummary && <div className={styles.featureSummary}>{featureSummary}</div>}

            {generatedFeatures.length > 0 && (
              <details className={styles.advanced}>
                <summary>Feature list (collapsed)</summary>
                <div className={styles.featureList}>
                  {generatedFeatures.map((f) => (
                    <div key={f.name} className={styles.featureItem}>
                      <div className={styles.featureName}>{f.name}</div>
                      <div className={styles.featureFormula}>{f.formula}</div>
                      <div className={styles.featureMeta}>{f.category}</div>
                    </div>
                  ))}
                </div>
              </details>
            )}

            <div className={styles.featureHeader}>
              <h4 className={styles.sectionTitle}>Results</h4>
              <p className={styles.hint}>Run analyze to view micro results, metrics, model, and MC.</p>
            </div>

            {!analysisResult && <p className={styles.hint}>Run “Analyze” to populate results.</p>}

            {analysisResult && (
              <div className={styles.analysisBlock}>
                <div className={styles.summaryRow}>
                  <span>
                    Sample size: <span className={styles.summaryValue}>{analysisResult.sample_size.toLocaleString()}</span>
                  </span>
                  <span>
                    Baseline rate: <span className={styles.summaryValue}>{(analysisResult.baseline_rate * 100).toFixed(1)}%</span>
                  </span>
                  <div className={styles.previewActions}>
                    <button type="button" className={styles.linkButton} onClick={handleDownloadMicroCsv} disabled={microCsvLoading}>
                      {microCsvLoading ? "Preparing micro CSV..." : "Download micro-model (CSV)"}
                    </button>
                    <button type="button" className={styles.linkButton} onClick={handleDownloadCsv} disabled={csvLoading}>
                      {csvLoading ? "Preparing feature CSV..." : "Download feature matrix (CSV)"}
                    </button>
                  </div>
                </div>
                <p className={styles.hint}>
                  Micro rows = per-game rows matching filters. Baseline = overall hit rate for the selected target.{" "}
                  <Link href={gamesLink} className={styles.linkButton} target="_blank">
                    View sample in games table
                  </Link>
                </p>

                {microRows && microRows.length > 0 ? (
                  <div className={styles.sectionCard}>
                    <h4 className={styles.sectionTitle}>Micro results (sample)</h4>
                    <p className={styles.hint}>Showing first 10 of {microRows.length.toLocaleString()} rows.</p>
                    <div className={styles.tableWrapper}>
                      <table className={styles.table}>
                        <thead>
                          <tr>
                            <th>Game</th>
                            <th>Side</th>
                            <th>Line</th>
                            <th>Odds</th>
                            <th>Outcome</th>
                            <th>EV%</th>
                            <th>Trigger</th>
                          </tr>
                        </thead>
                        <tbody>
                          {microRows.slice(0, 10).map((r) => (
                            <tr key={r.game_id}>
                              <td>{r.game_id}</td>
                              <td>{r.side}</td>
                              <td>{r.closing_line ?? "—"}</td>
                              <td>{r.closing_odds ?? "—"}</td>
                              <td>{r.outcome ?? "—"}</td>
                              <td>{r.est_ev_pct != null ? `${r.est_ev_pct.toFixed(1)}%` : "—"}</td>
                              <td>{r.trigger_flag ? "Yes" : "No"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <p className={styles.hint}>No micro rows yet for this filter set.</p>
                )}

                {theoryMetrics ? (
                  <div className={styles.sectionCard}>
                    <h4 className={styles.sectionTitle}>Metrics</h4>
                    <div className={styles.metricsGrid}>
                      <div>
                        Sample: <span className={styles.summaryValue}>{theoryMetrics.sample_size.toLocaleString()}</span>
                      </div>
                      <div>
                        Cover: <span className={styles.summaryValue}>{(theoryMetrics.cover_rate * 100).toFixed(1)}%</span>
                      </div>
                      {theoryMetrics.baseline_cover_rate != null && (
                        <div>
                          Baseline: <span className={styles.summaryValue}>{(theoryMetrics.baseline_cover_rate * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {theoryMetrics.delta_cover != null && (
                        <div>
                          Delta: <span className={styles.summaryValue}>{(theoryMetrics.delta_cover * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {theoryMetrics.ev_vs_implied != null && (
                        <div>
                          EV vs implied: <span className={styles.summaryValue}>{theoryMetrics.ev_vs_implied.toFixed(2)}%</span>
                        </div>
                      )}
                      {theoryMetrics.sharpe_like != null && (
                        <div>
                          Sharpe-like: <span className={styles.summaryValue}>{theoryMetrics.sharpe_like.toFixed(2)}</span>
                        </div>
                      )}
                      {theoryMetrics.max_drawdown != null && (
                        <div>
                          Max drawdown: <span className={styles.summaryValue}>{theoryMetrics.max_drawdown.toFixed(2)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className={styles.hint}>Run analyze to populate metrics.</p>
                )}
              </div>
            )}

            {modelResult ? (
              <div className={styles.analysisBlock}>
                <div className={styles.modelBlock}>
                  <h4 className={styles.sectionTitle}>Model summary</h4>
                  <div className={styles.summaryRow}>
                    <span>
                      Accuracy: <span className={styles.summaryValue}>{(modelResult.model_summary.accuracy * 100).toFixed(1)}%</span>
                    </span>
                    <span>
                      ROI: <span className={styles.summaryValue}>{(modelResult.model_summary.roi * 100).toFixed(1)}%</span>
                    </span>
                  </div>
                  <div className={styles.featureList}>
                    {Object.entries(modelResult.model_summary.feature_weights).map(([name, weight]) => (
                      <div key={name} className={styles.featureItem}>
                        <div className={styles.featureName}>{name}</div>
                        <div className={styles.featureFormula}>weight: {weight.toFixed(3)}</div>
                      </div>
                    ))}
                  </div>
                  <h4 className={styles.sectionTitle}>Suggested theories</h4>
                  {modelResult.suggested_theories.length === 0 && <p className={styles.hint}>No theories generated.</p>}
                  {modelResult.suggested_theories.length > 0 && (
                    <div className={styles.theoryList}>
                      {modelResult.suggested_theories.map((t, idx) => (
                        <div key={idx} className={styles.featureItem}>
                          <div className={styles.featureName}>{t.text}</div>
                          <div className={styles.hint}>Confidence: {t.confidence}</div>
                          <div className={styles.hint}>Edge: {(t.historical_edge * 100).toFixed(1)}%</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {mcSummary && (
                    <div className={styles.sectionCard}>
                      <h4 className={styles.sectionTitle}>Monte Carlo (historical)</h4>
                      <div className={styles.metricsGrid}>
                        <div>
                          Mean PnL: <span className={styles.summaryValue}>{mcSummary.mean_pnl.toFixed(2)}</span>
                        </div>
                        <div>
                          P5: <span className={styles.summaryValue}>{mcSummary.p5_pnl.toFixed(2)}</span>
                        </div>
                        <div>
                          P95: <span className={styles.summaryValue}>{mcSummary.p95_pnl.toFixed(2)}</span>
                        </div>
                        <div>
                          Actual: <span className={styles.summaryValue}>{mcSummary.actual_pnl.toFixed(2)}</span>
                        </div>
                        <div>
                          Luck score: <span className={styles.summaryValue}>{mcSummary.luck_score.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              analysisResult && <p className={styles.hint}>Build model to view model/MC outputs.</p>
            )}

            <details className={styles.advanced}>
              <summary>Advanced diagnostics</summary>
              <div className={styles.toggleRow}>
                <label className={styles.toggle}>
                  <input
                    type="checkbox"
                    checked={!!cleaningOptions.drop_if_any_null}
                    onChange={(e) => setCleaningOptions((prev) => ({ ...prev, drop_if_any_null: e.target.checked }))}
                  />
                  Drop rows with any missing feature
                </label>
                <label className={styles.toggle}>
                  <input
                    type="checkbox"
                    checked={!!cleaningOptions.drop_if_all_null}
                    onChange={(e) => setCleaningOptions((prev) => ({ ...prev, drop_if_all_null: e.target.checked }))}
                  />
                  Drop rows where all features are missing
                </label>
                <label className={styles.toggle}>
                  <input
                    type="checkbox"
                    checked={!!cleaningOptions.drop_if_non_numeric}
                    onChange={(e) => setCleaningOptions((prev) => ({ ...prev, drop_if_non_numeric: e.target.checked }))}
                  />
                  Drop rows with non-numeric feature values
                </label>
                <label className={styles.inlineField}>
                  Min non-null features
                  <input
                    className={styles.inputInline}
                    type="number"
                    min={0}
                    max={generatedFeatures.length || 1}
                    value={cleaningOptions.min_non_null_features ?? ""}
                    onChange={(e) =>
                      setCleaningOptions((prev) => ({
                        ...prev,
                        min_non_null_features: e.target.value === "" ? undefined : Number(e.target.value),
                      }))
                    }
                  />
                </label>
              </div>
              {dataQuality && (
                <div className={styles.dataQualityBlock}>
                  <div className={styles.summaryRow}>
                    <span>
                      Rows inspected: <span className={styles.summaryValue}>{dataQuality.rows_inspected.toLocaleString()}</span>
                    </span>
                    <div className={styles.previewActions}>
                      <input
                        className={styles.input}
                        style={{ maxWidth: 180 }}
                        placeholder="Filter features"
                        value={dqSearch}
                        onChange={(e) => setDqSearch(e.target.value)}
                      />
                      <select className={styles.select} value={dqSortKey} onChange={(e) => setDqSortKey(e.target.value as typeof dqSortKey)}>
                        <option value="null_pct">Sort by null %</option>
                        <option value="non_numeric">Sort by non-numeric</option>
                        <option value="name">Sort by name</option>
                      </select>
                      <select className={styles.select} value={dqSortDir} onChange={(e) => setDqSortDir(e.target.value as typeof dqSortDir)}>
                        <option value="desc">Desc</option>
                        <option value="asc">Asc</option>
                      </select>
                      <label className={styles.toggle}>
                        <input type="checkbox" checked={dqHideZero} onChange={(e) => setDqHideZero(e.target.checked)} />
                        Hide clean columns
                      </label>
                    </div>
                  </div>
                  <div className={styles.tableWrapper}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>Feature</th>
                          <th>Null %</th>
                          <th>Nulls</th>
                          <th>Non-numeric</th>
                          <th>Distinct</th>
                          <th>Count</th>
                          <th>Min</th>
                          <th>Max</th>
                          <th>Mean</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dataQualityRows.map((row) => (
                          <tr key={row.name}>
                            <td>{row.name}</td>
                            <td>{(row.null_pct * 100).toFixed(1)}%</td>
                            <td>{row.nulls}</td>
                            <td>{row.non_numeric}</td>
                            <td>{row.distinct_count}</td>
                            <td>{row.count}</td>
                            <td>{row.min !== null ? row.min.toFixed(3) : "—"}</td>
                            <td>{row.max !== null ? row.max.toFixed(3) : "—"}</td>
                            <td>{row.mean !== null ? row.mean.toFixed(3) : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              {analysisResult && (
                <div className={styles.sectionCard}>
                  <h4 className={styles.sectionTitle}>Correlations (diagnostic)</h4>
                  {analysisResult.correlations.length === 0 && <p className={styles.hint}>No strong correlations found.</p>}
                  {analysisResult.correlations.length > 0 && (
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>Feature</th>
                          <th>Corr</th>
                          <th>Significant</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysisResult.correlations.map((c) => (
                          <tr key={c.feature}>
                            <td>{c.feature}</td>
                            <td>{c.correlation.toFixed(3)}</td>
                            <td>{c.is_significant ? "Yes" : "No"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
              <div className={styles.previewActions}>
                <button type="button" className={styles.secondaryButton} onClick={handlePreviewCsv} disabled={!generatedFeatures.length || qualityLoading}>
                  Preview feature data (CSV)
                </button>
                <button type="button" className={styles.secondaryButton} onClick={handleLoadDataQuality} disabled={!generatedFeatures.length || qualityLoading}>
                  {qualityLoading ? "Loading data quality..." : "Data quality & cleaning"}
                </button>
                {qualityError && <div className={styles.error}>{qualityError}</div>}
              </div>
            </details>

            <div className={styles.actions}>
              <button type="button" className={styles.secondaryButton} onClick={handleReset}>
                Reset
              </button>
            </div>
          </div>
        </form>
      </AdminCard>
    </div>
  );
}



