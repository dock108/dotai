"use client";

import styles from "@/app/admin/theory-bets/eda/page.module.css";
import type { WalkforwardResponse } from "@/lib/api/sportsAdmin";

interface WalkforwardPanelProps {
  wfTrainDays: number;
  wfTestDays: number;
  wfStepDays: number;
  setWfTrainDays: (v: number) => void;
  setWfTestDays: (v: number) => void;
  setWfStepDays: (v: number) => void;
  wfRunning: boolean;
  isStatTarget: boolean;
  generatedFeaturesLength: number;
  wfError: string | null;
  wfResult: WalkforwardResponse | null;
  onRun: () => void;
}

export function WalkforwardPanel({
  wfTrainDays,
  wfTestDays,
  wfStepDays,
  setWfTrainDays,
  setWfTestDays,
  setWfStepDays,
  wfRunning,
  isStatTarget,
  generatedFeaturesLength,
  wfError,
  wfResult,
  onRun,
}: WalkforwardPanelProps) {
  return (
    <div className={styles.sectionCard}>
      <h4 className={styles.sectionTitle}>Walk-forward (blind replay)</h4>
      <p className={styles.hint}>
        Rolling train/test evaluation for out-of-sample performance. Market targets only.
      </p>
      <div className={styles.contextRow}>
        <label className={styles.inlineField}>
          Train days
          <input
            className={styles.inputInline}
            type="number"
            min={30}
            max={730}
            value={wfTrainDays}
            onChange={(e) => setWfTrainDays(Number(e.target.value) || 180)}
          />
        </label>
        <label className={styles.inlineField}>
          Test days
          <input
            className={styles.inputInline}
            type="number"
            min={3}
            max={90}
            value={wfTestDays}
            onChange={(e) => setWfTestDays(Number(e.target.value) || 14)}
          />
        </label>
        <label className={styles.inlineField}>
          Step days
          <input
            className={styles.inputInline}
            type="number"
            min={3}
            max={90}
            value={wfStepDays}
            onChange={(e) => setWfStepDays(Number(e.target.value) || 7)}
          />
        </label>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={onRun}
          disabled={wfRunning || isStatTarget || generatedFeaturesLength === 0}
          title={isStatTarget ? "Not eligible: stat targets have no market distribution" : undefined}
        >
          {wfRunning ? "Running walk-forward…" : "Run walk-forward"}
        </button>
      </div>
      {wfError && <div className={styles.error}>{wfError}</div>}
      {wfResult && (
        <>
          <div className={styles.metricsGrid}>
            <div>
              Edge half-life:{" "}
              <span className={styles.summaryValue}>
                {wfResult.edge_half_life_days != null ? `${wfResult.edge_half_life_days} days` : "n/a"}
              </span>
            </div>
            <div>
              Slices: <span className={styles.summaryValue}>{wfResult.slices.length}</span>
            </div>
            {wfResult.predictions_ref && (
              <div>
                <a className={styles.linkButton} href={wfResult.predictions_ref} target="_blank" rel="noreferrer">
                  Download predictions CSV
                </a>
              </div>
            )}
          </div>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Train end</th>
                  <th>Test end</th>
                  <th>N</th>
                  <th>Hit%</th>
                  <th>ROI (units)</th>
                  <th>Edge avg</th>
                  <th>Odds cov%</th>
                </tr>
              </thead>
              <tbody>
                {wfResult.slices.map((s, idx) => (
                  <tr key={idx}>
                    <td>{s.start_date ? String(s.start_date).slice(0, 10) : "—"}</td>
                    <td>{s.end_date ? String(s.end_date).slice(0, 10) : "—"}</td>
                    <td>{s.sample_size}</td>
                    <td>{s.hit_rate != null ? `${(s.hit_rate * 100).toFixed(1)}%` : "—"}</td>
                    <td>{s.roi_units != null ? s.roi_units.toFixed(2) : "—"}</td>
                    <td>{s.edge_avg != null ? s.edge_avg.toFixed(3) : "—"}</td>
                    <td>{s.odds_coverage_pct != null ? `${(s.odds_coverage_pct * 100).toFixed(1)}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

