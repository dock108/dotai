"use client";

import React from "react";
import styles from "@/app/admin/theory-bets/eda/page.module.css";
import type { ModelBuildResponse, McSummary } from "@/lib/api/sportsAdmin";

interface ModelResultsCardProps {
  modelResult: ModelBuildResponse;
  mcSummary: McSummary | null;
  primarySignalDrivers: { groupRows: { group: string; abs: number }[]; topDrivers: any[] } | null;
}

export function ModelResultsCard({ modelResult, mcSummary, primarySignalDrivers }: ModelResultsCardProps) {
  return (
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
          "Unit ROI (proxy)" is exploratory and not odds-calibrated; treat it as a rough sanity check, not a deployable profitability claim.
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
            <p className={styles.hint}>Exposure controls help simulate throttled capital deployment, but are not required for evaluation.</p>
          </div>
        )}

        {modelResult.bet_tape && modelResult.bet_tape.length > 0 && (
          <div className={styles.sectionCard}>
            <h4 className={styles.sectionTitle}>Bet tape (sample)</h4>
            <p className={styles.hint}>First 20 bets placed under selected exposure controls.</p>
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Game ID</th>
                    <th>Side</th>
                    <th>Line</th>
                    <th>Odds</th>
                    <th>Outcome</th>
                    <th>PnL</th>
                    <th>Cumulative</th>
                    <th>DD</th>
                  </tr>
                </thead>
                <tbody>
                  {modelResult.bet_tape.slice(0, 20).map((b: any, idx: number) => (
                    <tr key={`${b.game_id ?? "bet"}-${idx}`}>
                      <td>{String(b.game_date ?? "—").slice(0, 10)}</td>
                      <td>{b.game_id}</td>
                      <td>{b.side ?? "—"}</td>
                      <td>{b.line ?? "—"}</td>
                      <td>{b.odds ?? "—"}</td>
                      <td>{b.outcome}</td>
                      <td className={b.pnl < 0 ? styles.negative : styles.positive}>{b.pnl?.toFixed(2)}</td>
                      <td>{b.cumulative?.toFixed(2)}</td>
                      <td>{b.drawdown?.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {modelResult.performance_slices && (
          <div className={styles.sectionCard}>
            <h4 className={styles.sectionTitle}>Performance slices</h4>
            <p className={styles.hint}>Breakdown by confidence band / spread bucket / fav-underdog. High variance buckets may appear in red.</p>

            {modelResult.performance_slices.confidence?.length > 0 && (
              <>
                <h5 className={styles.sectionTitle}>By confidence band</h5>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Band</th>
                        <th>N</th>
                        <th>Hit%</th>
                        <th>ROI</th>
                        <th>Sharpe</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelResult.performance_slices.confidence.map((s: any) => (
                        <tr key={s.label} className={s.red_zone ? styles.redZoneRow : undefined}>
                          <td>{s.label}</td>
                          <td>{s.n}</td>
                          <td>{(s.hit_rate * 100).toFixed(1)}%</td>
                          <td>{(s.roi * 100).toFixed(1)}%</td>
                          <td>{s.sharpe?.toFixed(2) ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {modelResult.performance_slices.spread_buckets?.length > 0 && (
              <>
                <h5 className={styles.sectionTitle}>By spread bucket</h5>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Bucket</th>
                        <th>N</th>
                        <th>Hit%</th>
                        <th>ROI</th>
                        <th>Sharpe</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelResult.performance_slices.spread_buckets.map((s: any) => (
                        <tr key={s.label} className={s.red_zone ? styles.redZoneRow : undefined}>
                          <td>{s.label}</td>
                          <td>{s.n}</td>
                          <td>{(s.hit_rate * 100).toFixed(1)}%</td>
                          <td>{(s.roi * 100).toFixed(1)}%</td>
                          <td>{s.sharpe?.toFixed(2) ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {modelResult.performance_slices.favorite_vs_underdog?.length > 0 && (
              <>
                <h5 className={styles.sectionTitle}>Favorite vs underdog</h5>
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>N</th>
                        <th>Hit%</th>
                        <th>ROI</th>
                        <th>Sharpe</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelResult.performance_slices.favorite_vs_underdog.map((s: any) => (
                        <tr key={s.label} className={s.red_zone ? styles.redZoneRow : undefined}>
                          <td>{s.label}</td>
                          <td>{s.n}</td>
                          <td>{(s.hit_rate * 100).toFixed(1)}%</td>
                          <td>{(s.roi * 100).toFixed(1)}%</td>
                          <td>{s.sharpe?.toFixed(2) ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}

        {modelResult.failure_analysis && (
          <div className={styles.sectionCard}>
            <h4 className={styles.sectionTitle}>Failure analysis</h4>
            <div className={styles.metricsGrid}>
              <div>
                Largest loser:{" "}
                <span className={styles.summaryValue}>
                  {modelResult.failure_analysis.largest_loser != null ? modelResult.failure_analysis.largest_loser.toFixed(2) : "—"}
                </span>
              </div>
              <div>
                Loss streak (max):{" "}
                <span className={styles.summaryValue}>
                  {modelResult.failure_analysis.max_loss_streak ?? "—"}
                </span>
              </div>
            </div>
            {modelResult.failure_analysis.loss_streak_periods && modelResult.failure_analysis.loss_streak_periods.length > 0 && (
              <div className={styles.hintList}>
                {modelResult.failure_analysis.loss_streak_periods.slice(0, 5).map((p: any, i: number) => (
                  <div key={i}>
                    {p.start} → {p.end}: {p.streak} losses
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {mcSummary && (
          <div className={styles.sectionCard}>
            <h4 className={styles.sectionTitle}>Monte Carlo</h4>
            <div className={styles.metricsGrid}>
              <div>
                Mean PnL: <span className={styles.summaryValue}>{mcSummary.mean_pnl.toFixed(2)}</span>
              </div>
              <div>
                P5: <span className={styles.summaryValue}>{mcSummary.p5_pnl.toFixed(2)}</span>
              </div>
              {mcSummary.p50_pnl != null && (
                <div>
                  Median: <span className={styles.summaryValue}>{mcSummary.p50_pnl.toFixed(2)}</span>
                </div>
              )}
              <div>
                P95: <span className={styles.summaryValue}>{mcSummary.p95_pnl.toFixed(2)}</span>
              </div>
              <div>
                Actual: <span className={styles.summaryValue}>{mcSummary.actual_pnl.toFixed(2)}</span>
              </div>
              <div>
                Luck score: <span className={styles.summaryValue}>{mcSummary.luck_score.toFixed(2)}</span>
              </div>
              {mcSummary.mean_max_drawdown != null && (
                <div>
                  Mean max DD: <span className={styles.summaryValue}>{mcSummary.mean_max_drawdown.toFixed(2)}</span>
                </div>
              )}
              {mcSummary.actual_max_drawdown != null && (
                <div>
                  Actual max DD: <span className={styles.summaryValue}>{mcSummary.actual_max_drawdown.toFixed(2)}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

