"use client";

import React from "react";
import styles from "@/app/admin/theory-bets/eda/page.module.css";
import type { TheoryEvaluation, CohortInfo, TheoryMetrics } from "@/lib/api/sportsAdmin";

interface EvaluationCardProps {
  evaluation: TheoryEvaluation | null;
  cohort: CohortInfo | null;
  theoryMetrics: TheoryMetrics | null;
  isStat: boolean;
}

export function EvaluationCard({ evaluation, cohort, theoryMetrics, isStat }: EvaluationCardProps) {
  const formatValue = (val: number | null | undefined, formatting: "numeric" | "percent" = "numeric") => {
    if (val == null || Number.isNaN(val)) return "—";
    return formatting === "percent" ? `${(val * 100).toFixed(1)}%` : val.toFixed(1);
  };

  if (!evaluation) return null;

  const formatting = (evaluation as any).formatting === "percent" ? "percent" : "numeric";
  const evalData = evaluation as any;

  return (
    <>
      <div className={styles.sectionCard}>
        <h4 className={styles.sectionTitle}>Evaluation vs baseline</h4>
        <div className={styles.metricsGrid}>
          <div>
            Sample: <span className={styles.summaryValue}>{evalData.sample_size?.toLocaleString() ?? "—"}</span>
          </div>
          <div>
            Cohort mean: <span className={styles.summaryValue}>{formatValue(evalData.cohort_value, formatting)}</span>
          </div>
          <div>
            Baseline: <span className={styles.summaryValue}>{formatValue(evalData.baseline_value, formatting)}</span>
          </div>
          <div>
            Delta: <span className={styles.summaryValue}>{formatValue(evalData.delta_value ?? evalData.delta, formatting)}</span>
          </div>
          {!isStat && evalData.implied_rate != null && (
            <div>
              Implied rate: <span className={styles.summaryValue}>{(evalData.implied_rate * 100).toFixed(1)}%</span>
            </div>
          )}
          {!isStat && evalData.roi_units != null && (
            <div>
              ROI (units): <span className={styles.summaryValue}>{evalData.roi_units.toFixed(3)}</span>
            </div>
          )}
          {isStat && evalData.cohort_std != null && (
            <div>
              Std: <span className={styles.summaryValue}>{evalData.cohort_std.toFixed(2)}</span>
            </div>
          )}
          {isStat && evalData.cohort_min != null && (
            <div>
              Min: <span className={styles.summaryValue}>{evalData.cohort_min.toFixed(2)}</span>
            </div>
          )}
          {isStat && evalData.cohort_max != null && (
            <div>
              Max: <span className={styles.summaryValue}>{evalData.cohort_max.toFixed(2)}</span>
            </div>
          )}
        </div>
        {evalData.verdict && (
          <p className={styles.hint}>
            Verdict: <strong>{evalData.verdict}</strong>
          </p>
        )}
        {evalData.notes && Array.isArray(evalData.notes) && evalData.notes.length > 0 && (
          <p className={styles.hint}>{evalData.notes[0]}</p>
        )}
        {isStat && (
          <p className={styles.hint}>Stat-based target uses numeric values only; no rate/percentage semantics.</p>
        )}
      </div>

      {cohort && cohort.odds_coverage_pct != null && (
        <div className={styles.sectionCard}>
          <h4 className={styles.sectionTitle}>Odds coverage</h4>
          <div className={styles.metricsGrid}>
            <div>
              Coverage: <span className={styles.summaryValue}>{(cohort.odds_coverage_pct * 100).toFixed(1)}%</span>
            </div>
          </div>
          <p className={styles.hint}>Percentage of games with available odds for the selected market.</p>
        </div>
      )}

      {theoryMetrics && (
        <div className={styles.sectionCard}>
          <h4 className={styles.sectionTitle}>Theory Metrics</h4>
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
                Hit rate vs implied: <span className={styles.summaryValue}>{theoryMetrics.ev_vs_implied.toFixed(2)}%</span>
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
      )}
    </>
  );
}

