"use client";

import React from "react";
import styles from "@/app/admin/theory-bets/eda/page.module.css";
import type { MicroModelRow } from "@/lib/api/sportsAdmin";

interface MicroRowsTableProps {
  microRows: MicroModelRow[];
  downloadJson: (filename: string, data: any) => void;
}

export function MicroRowsTable({ microRows, downloadJson }: MicroRowsTableProps) {
  const isMarket = microRows.some((r) => r.market_type);

  return (
    <div className={styles.sectionCard}>
      <h4 className={styles.sectionTitle}>Micro rows (sample of {microRows.length})</h4>
      <div className={styles.previewActions}>
        <button type="button" className={styles.secondaryButton} onClick={() => downloadJson("micro_rows.json", microRows)}>
          Download JSON
        </button>
      </div>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Game</th>
              <th>Target</th>
              <th>Value</th>
              {isMarket && (
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
              const rowIsMarket = !!r.market_type;
              return (
                <tr key={`${r.game_id}-${r.target_name}`}>
                  <td>{r.game_id}</td>
                  <td>{r.target_name}</td>
                  <td>{r.target_value ?? "—"}</td>
                  {rowIsMarket && (
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
  );
}

