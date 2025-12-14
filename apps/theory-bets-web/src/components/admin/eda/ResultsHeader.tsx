"use client";

import styles from "@/app/admin/theory-bets/eda/page.module.css";
import type { AnalysisResponse, TargetDefinition, TheoryEvaluation } from "@/lib/api/sportsAdmin";

interface ResultsHeaderProps {
  analysisResult: AnalysisResponse | null;
  targetDefinition: TargetDefinition;
  evaluation: TheoryEvaluation | null;
  statusMessage: string | null;
  gamesLink: string;
  isStatTarget: boolean;
  csvLoading: boolean;
  microCsvLoading: boolean;
  onDownloadAnalysisCsv: () => void;
  onDownloadMicroCsv: () => void;
  onDownloadMicroJson: () => void;
  microRowsRef: string | null;
}

export function ResultsHeader({
  analysisResult,
  targetDefinition,
  evaluation,
  statusMessage,
  gamesLink,
  isStatTarget,
  csvLoading,
  microCsvLoading,
  onDownloadAnalysisCsv,
  onDownloadMicroCsv,
  onDownloadMicroJson,
  microRowsRef,
}: ResultsHeaderProps) {
  if (!analysisResult) return null;

  const workflowLabel = isStatTarget
    ? "Observational workflow: Analyze → Evaluation complete"
    : "Market workflow: Analyze → Evaluation → Build model → MC (optional)";

  const pipelineLabel = isStatTarget ? "stat" : "market";

  return (
    <div className={styles.sectionCard}>
      <h4 className={styles.sectionTitle}>Status &amp; downloads</h4>
      {statusMessage && <p className={styles.hint}>{statusMessage}</p>}
      <div className={styles.metricsGrid}>
        <div>
          Sample size: <span className={styles.summaryValue}>{analysisResult.sample_size}</span>
        </div>
        <div>
          Baseline:{" "}
          <span className={styles.summaryValue}>
            {isStatTarget
              ? `${(evaluation?.baseline_value ?? analysisResult.baseline_value).toFixed(2)} (numeric)`
              : `${((evaluation?.baseline_value ?? analysisResult.baseline_value) * 100).toFixed(1)}%`}
          </span>
        </div>
        <div>
          Pipeline step: <span className={styles.summaryValue}>{pipelineLabel}</span>
        </div>
      </div>
      <p className={styles.hint}>{workflowLabel}</p>

      {isStatTarget && evaluation && (
        <div className={styles.successBadge}>✅ Evaluation Complete</div>
      )}
      {!isStatTarget && evaluation && (
        <p className={styles.hint}>Evaluation done. Modeling/MC add depth, but are not required.</p>
      )}

      <div className={styles.previewActions}>
        <a className={styles.linkButton} href={gamesLink} target="_blank" rel="noreferrer">
          View matching games
        </a>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={onDownloadAnalysisCsv}
          disabled={csvLoading}
        >
          {csvLoading ? "Exporting…" : "Export analysis CSV"}
        </button>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={onDownloadMicroCsv}
          disabled={microCsvLoading}
        >
          {microCsvLoading ? "Exporting…" : "Export micro CSV"}
        </button>
        <button type="button" className={styles.secondaryButton} onClick={onDownloadMicroJson}>
          Download micro JSON
        </button>
        {microRowsRef && (
          <a className={styles.linkButton} href={microRowsRef} target="_blank" rel="noreferrer">
            Open persisted CSV
          </a>
        )}
      </div>
    </div>
  );
}

