import React from "react";
import styles from "@/app/admin/theory-bets/eda/page.module.css";
import { type AnalysisRunSummary } from "@/lib/api/sportsAdmin";

type Props = {
  savedRuns: AnalysisRunSummary[];
  runsLoading: boolean;
  runsError: string | null;
  onRefresh: () => void;
  onOpenLatest: () => void;
  onOpenRun: (runId: string) => void;
};

export function SavedRunsCard({ savedRuns, runsLoading, runsError, onRefresh, onOpenLatest, onOpenRun }: Props) {
  const hasRuns = savedRuns.length > 0;
  return (
    <div className={styles.sectionCard}>
      <div className={styles.sectionTitleRow}>
        <h4 className={styles.sectionTitle}>Saved runs</h4>
        <div className={styles.previewActions}>
          <button type="button" className={styles.secondaryButton} onClick={onRefresh} disabled={runsLoading}>
            {runsLoading ? "Refreshing..." : "Refresh"}
          </button>
          {hasRuns && (
            <button type="button" className={styles.linkButton} onClick={onOpenLatest}>
              Open latest
            </button>
          )}
        </div>
      </div>
      {runsError && <div className={styles.error}>{runsError}</div>}
      {!hasRuns && !runsError && <p className={styles.hint}>No saved runs yet.</p>}
      {hasRuns && (
        <div className={styles.checkboxGrid}>
          {savedRuns.slice(0, 10).map((run) => (
            <div key={run.run_id} className={styles.savedRunRow}>
              <div>
                <strong>{run.target_name ?? "unknown target"}</strong> · {run.run_type ?? "analyze"} ·{" "}
                {run.created_at ? new Date(run.created_at).toLocaleString() : "unknown time"}
                {run.snapshot_hash ? ` · snap ${run.snapshot_hash}` : ""}
              </div>
              <div className={styles.previewActions}>
                <button type="button" className={styles.linkButton} onClick={() => onOpenRun(run.run_id)}>
                  Open
                </button>
                {run.cohort_size != null && <span className={styles.countBadge}>N={run.cohort_size}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

