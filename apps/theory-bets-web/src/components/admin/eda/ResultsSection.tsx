import React from "react";
import styles from "../../../app/admin/theory-bets/eda/page.module.css";
import {
  type AnalysisResponse,
  type MicroModelRow,
  type TheoryMetrics,
  type ModelBuildResponse,
  type McSummary,
  type ModelingStatus,
  type MonteCarloStatus,
} from "@/lib/api/sportsAdmin";
import { MicroRowsTable } from "./MicroRowsTable";
import { EvaluationCard } from "./EvaluationCard";

type Props = {
  analysisResult: AnalysisResponse | null;
  microRows: MicroModelRow[] | null;
  theoryMetrics: TheoryMetrics | null;
  modelResult: ModelBuildResponse | null;
  primarySignalDrivers: { groupRows: { group: string; abs: number }[]; topDrivers: any[] } | null;
  gamesLink: string;
  microCsvLoading: boolean;
  csvLoading: boolean;
  onDownloadMicroCsv: () => void;
  onDownloadCsv: () => void;
  mcSummary: McSummary | null;
  theoryDraftEdits: Record<string, string>;
  theoryDraftStatus: Record<string, "draft" | "accepted" | "rejected">;
  setTheoryDraftEdits: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  setTheoryDraftStatus: React.Dispatch<React.SetStateAction<Record<string, "draft" | "accepted" | "rejected">>>;
  downloadJson: (filename: string, data: any) => void;
};

export function ResultsSection({
  analysisResult,
  microRows,
  theoryMetrics,
  modelResult,
  primarySignalDrivers,
  gamesLink,
  microCsvLoading,
  csvLoading,
  onDownloadMicroCsv,
  onDownloadCsv,
  mcSummary,
  theoryDraftEdits,
  theoryDraftStatus,
  setTheoryDraftEdits,
  setTheoryDraftStatus,
  downloadJson,
}: Props) {
  if (!analysisResult && !modelResult) {
    return <p className={styles.hint}>Run "Analyze" to populate results.</p>;
  }

  const evaluation = modelResult?.evaluation ?? analysisResult?.evaluation ?? null;
  const modeling: ModelingStatus | null = modelResult?.modeling ?? (analysisResult as any)?.modeling ?? null;
  const monteCarlo: MonteCarloStatus | null = modelResult?.monte_carlo ?? (analysisResult as any)?.monte_carlo ?? null;
  const notes: string[] | null = modelResult?.notes ?? (analysisResult as any)?.notes ?? null;
  const cohort = modelResult?.cohort ?? analysisResult?.cohort ?? null;
  const isStat = evaluation?.formatting === "numeric" || !(microRows?.some((r) => r.market_type));
  const detectedConcepts = analysisResult?.detected_concepts ?? null;
  const conceptFields = analysisResult?.concept_derived_fields ?? null;

  const renderModelingStatus = () => {
    if (!modeling) return null;
    return (
      <div className={styles.sectionCard}>
        <h4 className={styles.sectionTitle}>Modeling</h4>
        {!modeling.available && (
          <p className={styles.hint}>Not available: {modeling.reason_not_available ?? "unknown"}</p>
        )}
        {modeling.available && !modeling.has_run && (
          <p className={styles.hint}>
            Not run: {modeling.reason_not_run ?? "user_has_not_requested"}. Eligible: {JSON.stringify(modeling.eligibility ?? {})}
          </p>
        )}
        {modeling.available && modeling.has_run && (
          <>
            <div className={styles.metricsGrid}>
              <div>
                Accuracy: <span className={styles.summaryValue}>{modeling.metrics?.accuracy != null ? (modeling.metrics.accuracy * 100).toFixed(1) + "%" : "—"}</span>
              </div>
              <div>
                ROI: <span className={styles.summaryValue}>{modeling.metrics?.roi != null ? (modeling.metrics.roi * 100).toFixed(1) + "%" : "—"}</span>
              </div>
            </div>
            {modeling.feature_importance && modeling.feature_importance.length > 0 && (
              <p className={styles.hint}>Feature importance available (model trained).</p>
            )}
          </>
        )}
      </div>
    );
  };

  const renderMcStatus = () => {
    if (!monteCarlo) return null;
    return (
      <div className={styles.sectionCard}>
        <h4 className={styles.sectionTitle}>Monte Carlo</h4>
        {!monteCarlo.available && (
          <p className={styles.hint}>Not available: {monteCarlo.reason_not_available ?? "unknown"}</p>
        )}
        {monteCarlo.available && !monteCarlo.has_run && (
          <p className={styles.hint}>
            Not run: {monteCarlo.reason_not_run ?? "user_has_not_requested"}. Eligible: {JSON.stringify(monteCarlo.eligibility ?? {})}
          </p>
        )}
        {monteCarlo.available && monteCarlo.has_run && (
          <>
            <div className={styles.metricsGrid}>
              <div>P50 units: <span className={styles.summaryValue}>{monteCarlo.results?.p50_pnl ?? monteCarlo.results?.p50_units ?? "—"}</span></div>
              <div>P5 units: <span className={styles.summaryValue}>{monteCarlo.results?.p5_pnl ?? monteCarlo.results?.p5_units ?? "—"}</span></div>
              <div>P95 units: <span className={styles.summaryValue}>{monteCarlo.results?.p95_pnl ?? monteCarlo.results?.p95_units ?? "—"}</span></div>
            </div>
            {monteCarlo.results?.assumptions && (
              <p className={styles.hint}>
                Assumptions: bet sizing {monteCarlo.results.assumptions.bet_sizing}, ordering {monteCarlo.results.assumptions.ordering}, independence {String(monteCarlo.results.assumptions.independence)}.
              </p>
            )}
          </>
        )}
      </div>
    );
  };

  return (
    <div className={styles.resultsBlock}>
      {analysisResult && !modelResult && (
        <div className={styles.analysisBlock}>
          <div className={styles.summaryRow}>
            <span>Sample: <span className={styles.summaryValue}>{analysisResult.sample_size.toLocaleString()}</span></span>
            <a className={styles.linkButton} href={gamesLink} target="_blank" rel="noreferrer">View games</a>
          </div>

          {microRows && microRows.length > 0 ? (
            <MicroRowsTable microRows={microRows} downloadJson={downloadJson} />
          ) : (
            <p className={styles.hint}>No micro rows yet for this filter set.</p>
          )}

          <EvaluationCard evaluation={evaluation as any} cohort={cohort as any} theoryMetrics={theoryMetrics} isStat={isStat} />
          {detectedConcepts && detectedConcepts.length > 0 && (
            <div className={styles.sectionCard}>
              <h4 className={styles.sectionTitle}>Detected concepts</h4>
              <p className={styles.hint}>We derived the minimum data needed to evaluate these concepts:</p>
              <ul className={styles.bulletList}>
                {detectedConcepts.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
              {conceptFields && conceptFields.length > 0 && (
                <p className={styles.hint}>Auto-derived fields: {conceptFields.join(", ")}</p>
              )}
            </div>
          )}
          {renderModelingStatus()}
          {renderMcStatus()}

          {notes && notes.length > 0 && (
            <div className={styles.sectionCard}>
              <h4 className={styles.sectionTitle}>Notes</h4>
              <ul className={styles.bulletList}>
                {notes.map((n) => <li key={n}>{n}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {modelResult && (
        <div className={styles.analysisBlock}>
          <div className={styles.modelBlock}>
            <h4 className={styles.sectionTitle}>Model summary</h4>
            <div className={styles.summaryRow}>
              <span>Accuracy: <span className={styles.summaryValue}>{(modelResult.model_summary.accuracy * 100).toFixed(1)}%</span></span>
              <span>Unit ROI (proxy): <span className={styles.summaryValue}>{(modelResult.model_summary.roi * 100).toFixed(1)}%</span></span>
            </div>
            <p className={styles.hint}>"Unit ROI (proxy)" is exploratory and not odds-calibrated.</p>

            {primarySignalDrivers && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Primary Signal Drivers</h4>
                <div className={styles.metricsGrid}>
                  {primarySignalDrivers.groupRows.slice(0, 8).map((g) => (
                    <div key={g.group}>{g.group}: <span className={styles.summaryValue}>{g.abs.toFixed(3)}</span></div>
                  ))}
                </div>
              </div>
            )}

            {modelResult.features_dropped && modelResult.features_dropped.length > 0 && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Features dropped</h4>
                <p className={styles.hint}>{modelResult.features_dropped.length} features removed during pruning.</p>
              </div>
            )}

            {modelResult.exposure_summary && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Exposure summary</h4>
                <div className={styles.metricsGrid}>
                  <div>Triggered: <span className={styles.summaryValue}>{Number(modelResult.exposure_summary.triggered ?? 0).toLocaleString()}</span></div>
                  <div>Selected: <span className={styles.summaryValue}>{Number(modelResult.exposure_summary.selected ?? 0).toLocaleString()}</span></div>
                  <div>Days: <span className={styles.summaryValue}>{Number(modelResult.exposure_summary.unique_days ?? 0).toLocaleString()}</span></div>
                </div>
              </div>
            )}

            {modelResult.bet_tape && modelResult.bet_tape.length > 0 && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Bet tape (sample)</h4>
                <p className={styles.hint}>First {Math.min(10, modelResult.bet_tape.length)} bets.</p>
              </div>
            )}

            {modelResult.performance_slices && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Performance slices</h4>
                <p className={styles.hint}>Red zones indicate negative ROI or underperformance.</p>
              </div>
            )}

            {modelResult.failure_analysis && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Failure analysis</h4>
                <p className={styles.hint}>Largest losses and edge decay zones are logged.</p>
              </div>
            )}

            {mcSummary && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Monte Carlo summary</h4>
                <div className={styles.metricsGrid}>
                  <div>Mean PnL: <span className={styles.summaryValue}>{Number(mcSummary.mean_pnl ?? 0).toFixed(2)}</span></div>
                  {mcSummary.p50_pnl != null && <div>Median: <span className={styles.summaryValue}>{Number(mcSummary.p50_pnl).toFixed(2)}</span></div>}
                  <div>P5: <span className={styles.summaryValue}>{Number(mcSummary.p5_pnl ?? 0).toFixed(2)}</span></div>
                  <div>P95: <span className={styles.summaryValue}>{Number(mcSummary.p95_pnl ?? 0).toFixed(2)}</span></div>
                  <div>Luck: <span className={styles.summaryValue}>{Number(mcSummary.luck_score ?? 0).toFixed(2)}</span></div>
                  {mcSummary.mean_max_drawdown != null && <div>Mean max DD: <span className={styles.summaryValue}>{Number(mcSummary.mean_max_drawdown).toFixed(2)}</span></div>}
                  {mcSummary.actual_max_drawdown != null && <div>Actual max DD: <span className={styles.summaryValue}>{Number(mcSummary.actual_max_drawdown).toFixed(2)}</span></div>}
                </div>
              </div>
            )}

            {Array.isArray(modelResult.theory_candidates) && modelResult.theory_candidates.length > 0 && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Suggested theories</h4>
                <p className={styles.hint}>{modelResult.theory_candidates.length} candidates identified.</p>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr><th>Condition</th><th>Sample</th><th>Lift</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                      {modelResult.theory_candidates.slice(0, 5).map((c: any, idx: number) => {
                        const key = String(c.condition ?? idx);
                        const status = theoryDraftStatus[key] ?? "draft";
                        return (
                          <tr key={key}>
                            <td>{status === "accepted" ? "✅ " : status === "rejected" ? "❌ " : ""}{String(c.condition ?? "—")}</td>
                            <td>{Number(c.sample_size ?? 0).toLocaleString()}</td>
                            <td>{c.lift != null ? `${(Number(c.lift) * 100).toFixed(1)}%` : "—"}</td>
                            <td>
                              <button type="button" className={styles.linkButton} onClick={() => setTheoryDraftStatus((prev) => ({ ...prev, [key]: "accepted" }))}>Accept</button>
                              <button type="button" className={styles.linkButton} onClick={() => setTheoryDraftStatus((prev) => ({ ...prev, [key]: "rejected" }))}>Reject</button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
