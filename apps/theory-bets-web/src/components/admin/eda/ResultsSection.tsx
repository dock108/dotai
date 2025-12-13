import React from "react";
import Link from "next/link";
import styles from "../../../app/admin/theory-bets/eda/page.module.css";
import {
  type AnalysisResponse,
  type MicroModelRow,
  type TheoryMetrics,
  type ModelBuildResponse,
  type McSummary,
} from "@/lib/api/sportsAdmin";

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
    return <p className={styles.hint}>Run “Analyze” to populate results.</p>;
  }

  return (
    <>
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
              <button type="button" className={styles.linkButton} onClick={onDownloadMicroCsv} disabled={microCsvLoading}>
                {microCsvLoading ? "Preparing micro CSV..." : "Download micro-model (CSV)"}
              </button>
              <button type="button" className={styles.linkButton} onClick={onDownloadCsv} disabled={csvLoading}>
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
                      <th>Target</th>
                      <th>Value</th>
                      {microRows.some((r) => r.market_type) && (
                        <>
                          <th>Side</th>
                          <th>Line</th>
                          <th>Odds</th>
                          <th>Model p</th>
                          <th>Edge</th>
                          <th>EV%</th>
                        </>
                      )}
                      <th>Outcome</th>
                      <th>Trigger</th>
                      <th>Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {microRows.slice(0, 10).map((r) => {
                      const isMarket = !!r.market_type;
                      return (
                        <tr key={`${r.game_id}-${r.target_name}`}>
                          <td>{r.game_id}</td>
                          <td>{r.target_name}</td>
                          <td>{r.target_value ?? "—"}</td>
                          {isMarket && (
                            <>
                              <td>{r.side ?? "—"}</td>
                              <td>{r.closing_line ?? "—"}</td>
                              <td>{r.closing_odds ?? "—"}</td>
                              <td>{r.model_prob != null ? r.model_prob.toFixed(3) : "—"}</td>
                              <td>{r.edge_vs_implied != null ? r.edge_vs_implied.toFixed(3) : "—"}</td>
                              <td>{r.est_ev_pct != null ? `${r.est_ev_pct.toFixed(1)}%` : "—"}</td>
                            </>
                          )}
                          <td>{r.outcome ?? "—"}</td>
                          <td>{r.trigger_flag ? "Yes" : "No"}</td>
                          <td>{Array.isArray(r.meta?.trigger_reasons) ? r.meta?.trigger_reasons?.[0] ?? "—" : "—"}</td>
                        </tr>
                      );
                    })}
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
              <p className={styles.hint}>
                Accuracy/cover rate ≠ profitability. “Hit rate vs implied” is contextual under the selected odds assumption; max drawdown is a historical
                simulation artifact (order-dependent).
              </p>
            </div>
          ) : (
            <p className={styles.hint}>Run analyze to populate metrics.</p>
          )}
        </div>
      )}

      {modelResult && (
        <div className={styles.analysisBlock}>
          <div className={styles.modelBlock}>
            <h4 className={styles.sectionTitle}>Model summary</h4>
            <div className={styles.summaryRow}>
              <span>
                Accuracy: <span className={styles.summaryValue}>{(modelResult.model_summary.accuracy * 100).toFixed(1)}%</span>
              </span>
              <span>
                Unit ROI (proxy): <span className={styles.summaryValue}>{(modelResult.model_summary.roi * 100).toFixed(1)}%</span>
              </span>
            </div>
            <p className={styles.hint}>
              “Unit ROI (proxy)” is exploratory and not odds-calibrated; treat it as a rough sanity check, not a deployable profitability claim.
            </p>

            {primarySignalDrivers && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Primary Signal Drivers</h4>
                <p className={styles.hint}>Absolute weights aggregated by conceptual group (structure first, math later).</p>
                <div className={styles.metricsGrid}>
                  {primarySignalDrivers.groupRows.slice(0, 8).map((g) => (
                    <div key={g.group}>
                      {g.group}: <span className={styles.summaryValue}>{g.abs.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
                <p className={styles.hint}>Top drivers (max 7):</p>
                <div className={styles.featureList}>
                  {primarySignalDrivers.topDrivers.map((d) => (
                    <div key={d.name} className={styles.featureItem}>
                      <div className={styles.featureName}>
                        {d.name}
                        {d.timing === "post_game" ? " (leakage)" : ""}
                      </div>
                      <div className={styles.featureFormula}>
                        group: {d.group} · weight: {d.weight.toFixed(3)} · |w|: {d.abs.toFixed(3)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {modelResult.features_dropped && modelResult.features_dropped.length > 0 && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Features dropped (auto)</h4>
                <p className={styles.hint}>Noise removed during pruning (zero weight, duplicates, collinearity). This is logged explicitly.</p>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Feature</th>
                        <th>Reason</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelResult.features_dropped.slice(0, 50).map((d, idx) => (
                        <tr key={`${d.feature ?? "feature"}-${idx}`}>
                          <td>{String(d.feature ?? "—")}</td>
                          <td>{String(d.reason ?? "—")}</td>
                          <td>
                            {d.with ? `with: ${d.with}` : ""}
                            {d.abs_corr != null ? ` abs_corr: ${Number(d.abs_corr).toFixed(3)}` : ""}
                            {d.abs_weight != null ? ` abs_weight: ${Number(d.abs_weight).toExponential?.(2) ?? d.abs_weight}` : ""}
                            {d.non_nan != null ? ` non_nan: ${d.non_nan}` : ""}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {modelResult.features_dropped.length > 50 && (
                  <p className={styles.hint}>Showing first 50 of {modelResult.features_dropped.length.toLocaleString()} dropped features.</p>
                )}
              </div>
            )}

            {modelResult.exposure_summary && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Exposure summary</h4>
                <div className={styles.metricsGrid}>
                  <div>
                    Triggered: <span className={styles.summaryValue}>{Number(modelResult.exposure_summary.triggered ?? 0).toLocaleString()}</span>
                  </div>
                  <div>
                    Selected: <span className={styles.summaryValue}>{Number(modelResult.exposure_summary.selected ?? 0).toLocaleString()}</span>
                  </div>
                  <div>
                    Days: <span className={styles.summaryValue}>{Number(modelResult.exposure_summary.unique_days ?? 0).toLocaleString()}</span>
                  </div>
                  <div>
                    Avg/day: <span className={styles.summaryValue}>{Number(modelResult.exposure_summary.avg_bets_per_day ?? 0).toFixed(2)}</span>
                  </div>
                </div>
                {Array.isArray(modelResult.exposure_summary.warnings) && modelResult.exposure_summary.warnings.length > 0 && (
                  <div className={styles.warning}>
                    {modelResult.exposure_summary.warnings.slice(0, 3).map((w: any, i: number) => (
                      <div key={i}>{String(w)}</div>
                    ))}
                  </div>
                )}
                <p className={styles.hint}>
                  “Selected” is what would have been bet after exposure controls; it’s an artifact of this historical selection policy, not a production execution
                  engine.
                </p>
              </div>
            )}

            {modelResult.bet_tape && modelResult.bet_tape.length > 0 && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>What Would Have Been Bet (tape)</h4>
                <p className={styles.hint}>Representative sample (strong vs marginal) from selected bets.</p>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Strength</th>
                        <th>Date</th>
                        <th>Game</th>
                        <th>Side</th>
                        <th>Line</th>
                        <th>Odds</th>
                        <th>Model p</th>
                        <th>Implied p</th>
                        <th>Edge</th>
                        <th>Outcome</th>
                        <th>PnL</th>
                        <th>Why</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelResult.bet_tape.slice(0, 10).map((b: any, idx: number) => (
                        <tr key={`${b.game_id ?? "game"}-${idx}`}>
                          <td>{String(b.strength ?? "—")}</td>
                          <td>{b.date ? String(b.date).slice(0, 10) : "—"}</td>
                          <td>{b.game_id ?? "—"}</td>
                          <td>{b.side ?? "—"}</td>
                          <td>{b.line ?? "—"}</td>
                          <td>{b.odds ?? "—"}</td>
                          <td>{b.model_prob != null ? Number(b.model_prob).toFixed(3) : "—"}</td>
                          <td>{b.implied_prob != null ? Number(b.implied_prob).toFixed(3) : "—"}</td>
                          <td>{b.edge != null ? Number(b.edge).toFixed(3) : "—"}</td>
                          <td>{b.outcome ?? "—"}</td>
                          <td>{b.pnl_units != null ? Number(b.pnl_units).toFixed(2) : "—"}</td>
                          <td>{b.why ? String(b.why) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {modelResult.performance_slices && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Where This Model Wins / Loses</h4>
                <p className={styles.hint}>Red zones are slices with negative ROI or hit rate below implied.</p>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Slice</th>
                        <th>N</th>
                        <th>Hit%</th>
                        <th>ROI</th>
                        <th>Hit−Implied</th>
                        <th>Red</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(modelResult.performance_slices.confidence ?? []).map((s: any, idx: number) => (
                        <tr key={`conf-${idx}`}>
                          <td>{`Confidence: ${s.label}`}</td>
                          <td>{s.n ?? "—"}</td>
                          <td>{s.hit_rate != null ? `${(Number(s.hit_rate) * 100).toFixed(1)}%` : "—"}</td>
                          <td>{s.roi_units_per_bet != null ? Number(s.roi_units_per_bet).toFixed(2) : "—"}</td>
                          <td>{s.hit_minus_implied != null ? Number(s.hit_minus_implied).toFixed(3) : "—"}</td>
                          <td>{s.red_zone ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                      {(modelResult.performance_slices.spread_buckets ?? []).map((s: any, idx: number) => (
                        <tr key={`spread-${idx}`}>
                          <td>{`Spread: ${s.label}`}</td>
                          <td>{s.n ?? "—"}</td>
                          <td>{s.hit_rate != null ? `${(Number(s.hit_rate) * 100).toFixed(1)}%` : "—"}</td>
                          <td>{s.roi_units_per_bet != null ? Number(s.roi_units_per_bet).toFixed(2) : "—"}</td>
                          <td>{s.hit_minus_implied != null ? Number(s.hit_minus_implied).toFixed(3) : "—"}</td>
                          <td>{s.red_zone ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                      {(modelResult.performance_slices.favorite_vs_underdog ?? []).map((s: any, idx: number) => (
                        <tr key={`favud-${idx}`}>
                          <td>{`Fav/Dog: ${s.label}`}</td>
                          <td>{s.n ?? "—"}</td>
                          <td>{s.hit_rate != null ? `${(Number(s.hit_rate) * 100).toFixed(1)}%` : "—"}</td>
                          <td>{s.roi_units_per_bet != null ? Number(s.roi_units_per_bet).toFixed(2) : "—"}</td>
                          <td>{s.hit_minus_implied != null ? Number(s.hit_minus_implied).toFixed(3) : "—"}</td>
                          <td>{s.red_zone ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                      {(modelResult.performance_slices.pace_quartiles ?? []).map((s: any, idx: number) => (
                        <tr key={`pace-${idx}`}>
                          <td>{`Pace: ${s.label}`}</td>
                          <td>{s.n ?? "—"}</td>
                          <td>{s.hit_rate != null ? `${(Number(s.hit_rate) * 100).toFixed(1)}%` : "—"}</td>
                          <td>{s.roi_units_per_bet != null ? Number(s.roi_units_per_bet).toFixed(2) : "—"}</td>
                          <td>{s.hit_minus_implied != null ? Number(s.hit_minus_implied).toFixed(3) : "—"}</td>
                          <td>{s.red_zone ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {modelResult.failure_analysis && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Failure analysis</h4>
                <p className={styles.hint}>Ugly results are surfaced on purpose.</p>
                {Array.isArray(modelResult.failure_analysis.largest_losses) && modelResult.failure_analysis.largest_losses.length > 0 && (
                  <>
                    <p className={styles.hint}>Largest losses (sample):</p>
                    <div className={styles.tableWrapper}>
                      <table className={styles.table}>
                        <thead>
                          <tr>
                            <th>Date</th>
                            <th>Game</th>
                            <th>Side</th>
                            <th>Edge</th>
                            <th>Model p</th>
                            <th>PnL</th>
                            <th>Why</th>
                          </tr>
                        </thead>
                        <tbody>
                          {modelResult.failure_analysis.largest_losses.slice(0, 10).map((r: any, idx: number) => (
                            <tr key={`loss-${idx}`}>
                              <td>{r.date ? String(r.date).slice(0, 10) : "—"}</td>
                              <td>{r.game_id ?? "—"}</td>
                              <td>{r.side ?? "—"}</td>
                              <td>{r.edge != null ? Number(r.edge).toFixed(3) : "—"}</td>
                              <td>{r.model_prob != null ? Number(r.model_prob).toFixed(3) : "—"}</td>
                              <td>{r.pnl_units != null ? Number(r.pnl_units).toFixed(2) : "—"}</td>
                              <td>{r.why ? String(r.why) : "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
                {Array.isArray(modelResult.failure_analysis.edge_decay) && modelResult.failure_analysis.edge_decay.length > 0 && (
                  <>
                    <p className={styles.hint}>Edge decay zones:</p>
                    <div className={styles.tableWrapper}>
                      <table className={styles.table}>
                        <thead>
                          <tr>
                            <th>Bucket</th>
                            <th>N</th>
                            <th>Hit%</th>
                            <th>ROI</th>
                          </tr>
                        </thead>
                        <tbody>
                          {modelResult.failure_analysis.edge_decay.map((s: any, idx: number) => (
                            <tr key={`ed-${idx}`}>
                              <td>{s.label ?? "—"}</td>
                              <td>{s.n ?? "—"}</td>
                              <td>{s.hit_rate != null ? `${(Number(s.hit_rate) * 100).toFixed(1)}%` : "—"}</td>
                              <td>{s.roi_units_per_bet != null ? Number(s.roi_units_per_bet).toFixed(2) : "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </div>
            )}

            {mcSummary && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Monte Carlo summary</h4>
                <div className={styles.metricsGrid}>
                  <div>
                    Mean PnL: <span className={styles.summaryValue}>{Number(mcSummary.mean_pnl ?? 0).toFixed(2)}</span>
                  </div>
                  {mcSummary.p50_pnl != null && (
                    <div>
                      Median PnL: <span className={styles.summaryValue}>{Number(mcSummary.p50_pnl).toFixed(2)}</span>
                    </div>
                  )}
                  <div>
                    p5 PnL: <span className={styles.summaryValue}>{Number(mcSummary.p5_pnl ?? 0).toFixed(2)}</span>
                  </div>
                  <div>
                    p95 PnL: <span className={styles.summaryValue}>{Number(mcSummary.p95_pnl ?? 0).toFixed(2)}</span>
                  </div>
                  <div>
                    Luck score: <span className={styles.summaryValue}>{Number(mcSummary.luck_score ?? 0).toFixed(2)}</span>
                  </div>
                </div>
                <p className={styles.hint}>
                  This is a distribution of outcomes, not a promise. Assumes independence and uses a simplified win/loss unit model.
                </p>
              </div>
            )}

            {Array.isArray(modelResult.theory_candidates) && modelResult.theory_candidates.length > 0 && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Suggested theories (candidates)</h4>
                <p className={styles.hint}>Drafts are editable; accept/reject is local-only.</p>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Draft</th>
                        <th>Sample</th>
                        <th>Lift</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelResult.theory_candidates.slice(0, 10).map((t: any, idx: number) => {
                        const id = t.id ?? `theory-${idx}`;
                        const status = theoryDraftStatus[id] ?? "draft";
                        const draft = theoryDraftEdits[id] ?? t.draft ?? "";
                        return (
                          <tr key={id}>
                            <td>
                              <textarea
                                className={styles.textarea}
                                value={draft}
                                onChange={(e) =>
                                  setTheoryDraftEdits((prev) => ({
                                    ...prev,
                                    [id]: e.target.value,
                                  }))
                                }
                              />
                            </td>
                            <td>{t.sample_size != null ? Number(t.sample_size).toLocaleString() : "—"}</td>
                            <td>{t.lift != null ? `${(Number(t.lift) * 100).toFixed(1)}%` : "—"}</td>
                            <td>
                              <div className={styles.buttonStack}>
                                <button
                                  type="button"
                                  className={styles.secondaryButton}
                                  onClick={() => setTheoryDraftStatus((prev) => ({ ...prev, [id]: "accepted" }))}
                                >
                                  Accept
                                </button>
                                <button
                                  type="button"
                                  className={styles.secondaryButton}
                                  onClick={() => setTheoryDraftStatus((prev) => ({ ...prev, [id]: "rejected" }))}
                                >
                                  Reject
                                </button>
                                <div className={styles.hint}>Status: {status}</div>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {modelResult.model_snapshot && (
              <div className={styles.sectionCard}>
                <h4 className={styles.sectionTitle}>Snapshot & reproducibility</h4>
                <div className={styles.metricsGrid}>
                  <div>
                    Snapshot hash: <span className={styles.summaryValue}>{String(modelResult.model_snapshot.hash ?? "—")}</span>
                  </div>
                  <div>
                    Created:{" "}
                    <span className={styles.summaryValue}>
                      {modelResult.model_snapshot.payload?.created_at ? String(modelResult.model_snapshot.payload.created_at) : "—"}
                    </span>
                  </div>
                </div>
                <div className={styles.previewActions}>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() =>
                      downloadJson(
                        `model-snapshot-${String(modelResult.model_snapshot?.hash ?? "snapshot")}.json`,
                        modelResult.model_snapshot
                      )
                    }
                  >
                    Download snapshot (JSON)
                  </button>
                </div>
                <p className={styles.hint}>This is the replayable payload for results: filters + features + target + trigger + exposure + cleaning.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

