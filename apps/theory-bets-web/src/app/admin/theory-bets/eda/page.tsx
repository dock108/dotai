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
  fetchDataQuality,
  type AvailableStatKeysResponse,
  type GeneratedFeature,
  type AnalysisResponse,
  type ModelBuildResponse,
  type CleaningOptions,
  type DataQualitySummary,
} from "@/lib/api/sportsAdmin";

type FormState = {
  leagueCode: LeagueCode;
  season: string;
  startDate: string;
  endDate: string;
  team: string;
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
  season: "",
  startDate: "",
  endDate: "",
  team: "",
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
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [dataQuality, setDataQuality] = useState<DataQualitySummary | null>(null);
  const [qualityError, setQualityError] = useState<string | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
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
    if (form.season.trim()) params.set("season", form.season.trim());
    if (form.startDate.trim()) params.set("startDate", form.startDate.trim());
    if (form.endDate.trim()) params.set("endDate", form.endDate.trim());
    if (form.team.trim()) params.set("team", form.team.trim());
    const qs = params.toString();
    return `/admin/theory-bets/games${qs ? `?${qs}` : ""}`;
  }, [form.leagueCode, form.season, form.startDate, form.endDate, form.team]);

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

  const handleGenerateFeatures = async () => {
    setFeatureError(null);
    setAnalysisResult(null);
    setAnalysisError(null);
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
        seasons: form.season ? [Number(form.season)] : undefined,
        cleaning: cleaningOptions,
      });
      setAnalysisResult(res);
      setModelResult(null);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err));
      setAnalysisResult(null);
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
        seasons: form.season ? [Number(form.season)] : undefined,
        target: analysisTarget,
        limit: 1000,
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
        seasons: form.season ? [Number(form.season)] : undefined,
        limit: 1000,
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
        seasons: form.season ? [Number(form.season)] : undefined,
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

  const handleBuildModel = async () => {
    setModelLoading(true);
    setModelError(null);
    try {
      const res = await buildModel({
        league_code: form.leagueCode,
        features: generatedFeatures,
        target: analysisTarget,
        seasons: form.season ? [Number(form.season)] : undefined,
        cleaning: cleaningOptions,
      });
      setModelResult(res);
    } catch (err) {
      setModelError(err instanceof Error ? err.message : String(err));
      setModelResult(null);
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
    setModelResult(null);
    setModelError(null);
    setError(null);
    setDataQuality(null);
    setQualityError(null);
    setCleaningOptions({
      drop_if_all_null: false,
      drop_if_any_null: false,
      drop_if_non_numeric: false,
      min_non_null_features: undefined,
    });
  };

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
              <label className={styles.label}>Season (optional)</label>
              <input
                className={styles.input}
                type="number"
                value={form.season}
                onChange={(e) => setForm((prev) => ({ ...prev, season: e.target.value }))}
                placeholder="2024"
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Start date</label>
              <input
                className={styles.input}
                type="date"
                value={form.startDate}
                onChange={(e) => setForm((prev) => ({ ...prev, startDate: e.target.value }))}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>End date</label>
              <input
                className={styles.input}
                type="date"
                value={form.endDate}
                onChange={(e) => setForm((prev) => ({ ...prev, endDate: e.target.value }))}
              />
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

          <div className={styles.featureSection}>
            <div className={styles.featureHeader}>
              <h3 className={styles.sectionTitle}>Step 1: Generate features</h3>
              <p className={styles.hint}>
                Select basic stats, choose context, then generate derived features the system will use.
              </p>
            </div>

            <div className={styles.contextRow}>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={includeRestDays}
                  onChange={(e) => setIncludeRestDays(e.target.checked)}
                />
                Include rest days
              </label>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={includeRolling}
                  onChange={(e) => setIncludeRolling(e.target.checked)}
                />
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
            </div>

            {featureError && <div className={styles.error}>{featureError}</div>}
            {featureSummary && <div className={styles.featureSummary}>{featureSummary}</div>}

            {generatedFeatures.length > 0 && (
              <div className={styles.previewActions}>
                <button type="button" className={styles.secondaryButton} onClick={handlePreviewCsv}>
                  Preview feature data (CSV)
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={handleLoadDataQuality}
                  disabled={qualityLoading}
                >
                  {qualityLoading ? "Loading data quality..." : "Data quality & cleaning"}
                </button>
                {qualityError && <div className={styles.error}>{qualityError}</div>}
              </div>
            )}

            {dataQuality && (
              <div className={styles.dataQualityBlock}>
                <div className={styles.summaryRow}>
                  <span>
                    Rows inspected:{" "}
                    <span className={styles.summaryValue}>{dataQuality.rows_inspected.toLocaleString()}</span>
                  </span>
                  <span className={styles.hint}>Preview is capped to the first 1,000 rows.</span>
                </div>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Feature</th>
                        <th>Null %</th>
                        <th>Nulls</th>
                        <th>Non-numeric</th>
                        <th>Count</th>
                        <th>Min</th>
                        <th>Max</th>
                        <th>Mean</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(dataQuality.feature_stats).map(([name, stats]) => (
                        <tr key={name}>
                          <td>{name}</td>
                          <td>{(stats.null_pct * 100).toFixed(1)}%</td>
                          <td>{stats.nulls}</td>
                          <td>{stats.non_numeric}</td>
                          <td>{stats.count}</td>
                          <td>{stats.min !== null ? stats.min.toFixed(3) : "—"}</td>
                          <td>{stats.max !== null ? stats.max.toFixed(3) : "—"}</td>
                          <td>{stats.mean !== null ? stats.mean.toFixed(3) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {generatedFeatures.length > 0 && (
              <div className={styles.featureList}>
                {generatedFeatures.map((f) => (
                  <div key={f.name} className={styles.featureItem}>
                    <div className={styles.featureName}>{f.name}</div>
                    <div className={styles.featureFormula}>{f.formula}</div>
                    <div className={styles.featureMeta}>{f.category}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {generatedFeatures.length > 0 && (
            <div className={styles.featureSection}>
              <div className={styles.featureHeader}>
                <h3 className={styles.sectionTitle}>Step 2: Run analysis</h3>
                <p className={styles.hint}>Check which generated features correlate with the chosen target.</p>
              </div>
              <div className={styles.contextRow}>
                <label className={styles.inlineField}>
                  Target
                  <select
                    className={styles.select}
                    value={analysisTarget}
                    onChange={(e) => setAnalysisTarget(e.target.value as "cover" | "win" | "over")}
                  >
                    <option value="cover">Cover (spread)</option>
                    <option value="win">Win (moneyline)</option>
                    <option value="over">Over (total)</option>
                  </select>
                </label>
                <button type="button" className={styles.primaryButton} onClick={handleRunAnalysis} disabled={analysisLoading}>
                  {analysisLoading ? "Running analysis..." : "Run analysis"}
                </button>
              </div>

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

              {analysisError && <div className={styles.error}>{analysisError}</div>}
              {analysisResult && (
                <div className={styles.analysisBlock}>
                  <div className={styles.summaryRow}>
                    <span>
                      Sample size: <span className={styles.summaryValue}>{analysisResult.sample_size.toLocaleString()}</span>
                    </span>
                    <span>
                      Baseline rate:{" "}
                      <span className={styles.summaryValue}>{(analysisResult.baseline_rate * 100).toFixed(1)}%</span>
                    </span>
                    {analysisResult.cleaning_summary && (
                      <span className={styles.hint}>
                        Cleaned: {analysisResult.cleaning_summary.rows_after_cleaning.toLocaleString()} of{" "}
                        {analysisResult.cleaning_summary.raw_rows.toLocaleString()} rows (
                        {analysisResult.cleaning_summary.dropped_null} dropped for nulls,{" "}
                        {analysisResult.cleaning_summary.dropped_non_numeric} for non-numeric)
                      </span>
                    )}
                  <button
                    type="button"
                    className={styles.linkButton}
                    onClick={handleDownloadCsv}
                    disabled={csvLoading}
                  >
                    {csvLoading ? "Preparing CSV..." : "Download feature matrix (CSV)"}
                  </button>
                  </div>
                  <p className={styles.hint}>
                    Sample size = games with a computed target. Baseline = overall hit rate for the selected target.
                    {" "}
                    <Link href={gamesLink} className={styles.linkButton} target="_blank">
                      View sample in games table
                    </Link>
                  </p>

                  <div className={styles.analysisGrid}>
                    <div>
                      <h4 className={styles.sectionTitle}>Top correlations</h4>
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
                    <div>
                      <h4 className={styles.sectionTitle}>Insights</h4>
                      {analysisResult.insights.length === 0 && <p className={styles.hint}>No insights yet.</p>}
                      {analysisResult.insights.length > 0 && (
                        <ul className={styles.insightsList}>
                          {analysisResult.insights.map((i, idx) => (
                            <li key={idx}>{i}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                  <div className={styles.actions}>
                    <button type="button" className={styles.primaryButton} onClick={handleBuildModel} disabled={modelLoading}>
                      {modelLoading ? "Building model..." : "Build model"}
                    </button>
                  </div>
                  {modelError && <div className={styles.error}>{modelError}</div>}
                  {modelResult && (
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
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className={styles.actions}>
            <button type="button" className={styles.secondaryButton} onClick={handleReset}>
              Reset
            </button>
          </div>
        </form>
      </AdminCard>
    </div>
  );
}



