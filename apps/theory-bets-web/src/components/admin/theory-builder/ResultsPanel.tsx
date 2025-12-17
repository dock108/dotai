"use client";

import React, { useState, useCallback, useMemo } from "react";
import styles from "./TheoryBuilder.module.css";
import type { TheoryBuilderState, TheoryBuilderActions } from "./useTheoryBuilderState";

interface Props {
  state: TheoryBuilderState;
  actions: TheoryBuilderActions;
}

// Human-readable target descriptions
const TARGET_DESCRIPTIONS: Record<string, string> = {
  game_total: "Game total (combined points)",
  spread_result: "Spread cover",
  moneyline_win: "Moneyline win",
  team_stat: "Team statistic",
};

// Human-readable concept explanations
const CONCEPT_EXPLANATIONS: Record<string, { label: string; description: string }> = {
  pace: {
    label: "Pace",
    description: "This theory appears sensitive to game tempo (estimated possessions per game) rather than shooting efficiency.",
  },
  rest: {
    label: "Rest advantage",
    description: "Days between games may influence outcomes. Rest advantage is factored in.",
  },
  altitude: {
    label: "Altitude",
    description: "Venue altitude differences may affect team performance.",
  },
};

export function ResultsPanel({ state, actions }: Props) {
  const { analysisResult, draft } = state;
  const [showCorrelations, setShowCorrelations] = useState(false);
  const [showAllMicroRows, setShowAllMicroRows] = useState(false);

  const downloadJson = useCallback((filename: string, data: unknown) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  }, []);

  // Build verdict reasons
  const verdictReasons = useMemo(() => {
    if (!analysisResult) return [];
    const reasons: { type: "good" | "warning" | "bad"; text: string }[] = [];
    const delta = analysisResult.delta_value ?? 0;
    const sample = analysisResult.sample_size ?? 0;
    const evaluation = analysisResult.evaluation ?? {};

    // Lift
    if (delta > 0.1) {
      reasons.push({ type: "good", text: `Strong lift (+${(delta * 100).toFixed(1)}%)` });
    } else if (delta > 0.05) {
      reasons.push({ type: "good", text: `Moderate lift (+${(delta * 100).toFixed(1)}%)` });
    } else if (delta > 0) {
      reasons.push({ type: "warning", text: `Small lift (+${(delta * 100).toFixed(1)}%)` });
    } else {
      reasons.push({ type: "bad", text: `Negative lift (${(delta * 100).toFixed(1)}%)` });
    }

    // Sample size
    if (sample >= 5000) {
      reasons.push({ type: "good", text: `Large sample (${sample.toLocaleString()} games)` });
    } else if (sample >= 1000) {
      reasons.push({ type: "warning", text: `Moderate sample (${sample.toLocaleString()} games)` });
    } else {
      reasons.push({ type: "bad", text: `Small sample (${sample.toLocaleString()} games)` });
    }

    // Stability (if available and not [object Object])
    const stability = evaluation.stability_by_season;
    if (stability && typeof stability === "object" && !Array.isArray(stability)) {
      const values = Object.values(stability).filter((v) => typeof v === "number") as number[];
      if (values.length > 1) {
        const variance =
          values.reduce((sum, v) => sum + Math.pow(v - delta, 2), 0) / values.length;
        if (variance < 0.01) {
          reasons.push({ type: "good", text: "Stable across seasons" });
        } else if (variance < 0.05) {
          reasons.push({ type: "warning", text: "Moderate stability across seasons" });
        } else {
          reasons.push({ type: "bad", text: "Unstable across seasons" });
        }
      }
    }

    // Correlations strength
    const correlations = analysisResult.correlations ?? [];
    const significantCount = correlations.filter((c) => c.significant).length;
    if (significantCount === 0) {
      reasons.push({
        type: "warning",
        text: "No significant linear correlations (may be interaction-based)",
      });
    } else if (significantCount >= 3) {
      reasons.push({ type: "good", text: `${significantCount} significant feature correlations` });
    }

    return reasons;
  }, [analysisResult]);

  if (!analysisResult) {
    return (
      <div className={styles.resultsPanel}>
        <div className={styles.emptyResults}>
          <h3>No results yet</h3>
          <p>Define your theory and run analysis to see results here.</p>
        </div>
      </div>
    );
  }

  const correlations = analysisResult.correlations ?? [];
  const microRows = analysisResult.micro_rows ?? [];
  const evaluation = analysisResult.evaluation ?? {};

  // Only show top 3 correlations by default
  const displayCorrelations = correlations.slice(0, 3);
  const displayMicroRows = showAllMicroRows ? microRows : microRows.slice(0, 10);

  // Human-readable outcome description
  const targetDesc = TARGET_DESCRIPTIONS[draft.target.type] ?? draft.target.type;
  const sideDesc = draft.target.side ? ` (${draft.target.side})` : "";
  const outcomeLabel = `${targetDesc}${sideDesc}`;

  // Summary sentence
  const baseline = analysisResult.baseline_value;
  const cohort = analysisResult.cohort_value;
  const delta = analysisResult.delta_value;
  const liftPct = delta != null ? (delta * 100).toFixed(1) : null;

  return (
    <div className={styles.resultsPanel}>
      {/* Outcome evaluated */}
      <div className={styles.outcomeHeader}>
        <span className={styles.outcomeLabel}>Outcome evaluated:</span>
        <span className={styles.outcomeValue}>{outcomeLabel}</span>
      </div>

      {/* Summary sentence */}
      {cohort != null && baseline != null && delta != null && (
        <p className={styles.summarySentence}>
          Games matching this theory{" "}
          {draft.target.type === "spread_result"
            ? `covered the spread ${(cohort * 100).toFixed(1)}% of the time`
            : draft.target.type === "moneyline_win"
              ? `won ${(cohort * 100).toFixed(1)}% of the time`
              : `averaged ${cohort.toFixed(2)}`}
          , compared to a {(baseline * 100).toFixed(1)}% baseline
          {delta > 0 ? `, a +${liftPct}% lift` : `, a ${liftPct}% difference`}.
        </p>
      )}

      {/* Summary Cards - simplified */}
      <div className={styles.summaryCards}>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Sample</span>
          <span className={styles.summaryValue}>
            {analysisResult.sample_size.toLocaleString()}
          </span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Baseline</span>
          <span className={styles.summaryValue}>{(baseline * 100).toFixed(1)}%</span>
        </div>
        {cohort != null && (
          <div className={styles.summaryCard}>
            <span className={styles.summaryLabel}>Cohort</span>
            <span className={styles.summaryValue}>{(cohort * 100).toFixed(1)}%</span>
          </div>
        )}
        {delta != null && (
          <div className={styles.summaryCard}>
            <span className={styles.summaryLabel}>Lift</span>
            <span
              className={`${styles.summaryValue} ${delta > 0 ? styles.positive : styles.negative}`}
            >
              {delta > 0 ? "+" : ""}
              {liftPct}%
            </span>
          </div>
        )}
      </div>

      {/* Verdict - structured */}
      {verdictReasons.length > 0 && (
        <div className={styles.verdictSection}>
          <h4 className={styles.subsectionTitle}>Assessment</h4>
          <ul className={styles.verdictList}>
            {verdictReasons.map((reason, i) => (
              <li key={i} className={styles[`verdict${reason.type}`]}>
                <span className={styles.verdictIcon}>
                  {reason.type === "good" ? "✓" : reason.type === "warning" ? "⚠" : "✗"}
                </span>
                {reason.text}
              </li>
            ))}
          </ul>
          {verdictReasons.filter((r) => r.type === "good").length >= 2 && (
            <div className={styles.verdictCta}>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={() => actions.setActiveTab("run")}
              >
                Build model →
              </button>
            </div>
          )}
        </div>
      )}

      {/* Detected concepts - with explanations */}
      {analysisResult.detected_concepts.length > 0 && (
        <div className={styles.conceptsSection}>
          <h4 className={styles.subsectionTitle}>Detected patterns</h4>
          {analysisResult.detected_concepts.map((concept) => {
            const info = CONCEPT_EXPLANATIONS[concept];
            return (
              <div key={concept} className={styles.conceptExplainer}>
                <span className={styles.conceptLabel}>{info?.label ?? concept}</span>
                <p className={styles.conceptDesc}>
                  {info?.description ?? "Pattern detected in your theory inputs."}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* ROI - only if meaningful, with clear units */}
      {evaluation.roi != null && typeof evaluation.roi === "number" && (
        <div className={styles.roiSection}>
          <div className={styles.roiCard}>
            <span className={styles.roiLabel}>Simulated ROI (flat 1u staking)</span>
            <span
              className={`${styles.roiValue} ${evaluation.roi > 0 ? styles.positive : styles.negative}`}
            >
              {evaluation.roi > 0 ? "+" : ""}
              {(evaluation.roi * 100).toFixed(1)}%
            </span>
            <p className={styles.roiNote}>
              Based on historical closing lines. Does not account for vig or line movement.
            </p>
          </div>
        </div>
      )}

      {/* Correlations - collapsed by default, diagnostic framing */}
      {correlations.length > 0 && (
        <details className={styles.correlationsSection}>
          <summary className={styles.correlationsSummary}>
            <span>Feature correlations (diagnostic)</span>
            <span className={styles.correlationsHint}>
              For intuition only — correlation ≠ predictive power
            </span>
          </summary>
          <div className={styles.correlationsContent}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Correlation</th>
                </tr>
              </thead>
              <tbody>
                {(showCorrelations ? correlations : displayCorrelations).map((c) => (
                  <tr key={c.feature}>
                    <td>{c.feature.replace(/_/g, " ")}</td>
                    <td className={c.correlation > 0 ? styles.positive : styles.negative}>
                      {c.correlation.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {correlations.length > 3 && (
              <button
                type="button"
                className={styles.linkButton}
                onClick={() => setShowCorrelations(!showCorrelations)}
              >
                {showCorrelations ? "Show top 3" : `Show all ${correlations.length}`}
              </button>
            )}
          </div>
        </details>
      )}

      {/* Micro rows - with context */}
      {microRows.length > 0 && (
        <div className={styles.microRowsSection}>
          <div className={styles.sectionHeader}>
            <h4 className={styles.subsectionTitle}>
              Sample games ({microRows.length.toLocaleString()})
            </h4>
            <div className={styles.sectionActions}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => downloadJson("sample_games.json", microRows)}
              >
                Export
              </button>
            </div>
          </div>
          <div className={styles.microRowsTable}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Home</th>
                  <th>Score</th>
                  <th>Away</th>
                  <th>Score</th>
                  <th>{targetDesc}</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {displayMicroRows.map((row, i) => (
                  <tr key={`${row.game_id}-${i}`}>
                    <td>{row.game_date ? String(row.game_date) : "—"}</td>
                    <td>{row.home_team ? String(row.home_team) : "—"}</td>
                    <td>{row.home_score != null ? String(row.home_score) : "—"}</td>
                    <td>{row.away_team ? String(row.away_team) : "—"}</td>
                    <td>{row.away_score != null ? String(row.away_score) : "—"}</td>
                    <td>
                      {row.target_value != null
                        ? typeof row.target_value === "number"
                          ? row.target_value.toFixed(2)
                          : String(row.target_value)
                        : "—"}
                    </td>
                    <td className={String(row.outcome) === "W" ? styles.positive : styles.negative}>
                      {row.outcome != null ? String(row.outcome) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {microRows.length > 10 && (
            <button
              type="button"
              className={styles.linkButton}
              onClick={() => setShowAllMicroRows(!showAllMicroRows)}
            >
              {showAllMicroRows ? "Show fewer" : `Show all ${microRows.length.toLocaleString()}`}
            </button>
          )}
        </div>
      )}

      {/* Export section */}
      <div className={styles.exportSection}>
        <h4 className={styles.subsectionTitle}>Export</h4>
        <div className={styles.exportButtons}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => downloadJson("theory_analysis.json", analysisResult)}
          >
            Download Full Analysis
          </button>
        </div>
      </div>
    </div>
  );
}
