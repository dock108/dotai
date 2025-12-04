"use client";

import { useMemo, useState } from "react";
import styles from "./page.module.css";
import { AdminCard, LoadingState, ErrorState } from "@/components/admin";
import { SUPPORTED_LEAGUES, type LeagueCode } from "@/lib/constants/sports";
import { runEdaQuery, type EDAFilters, type EDAGameRow } from "@/lib/api/sportsAdmin";

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
  teamStatKeys: string;
  playerStatKeys: string;
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
  teamStatKeys: "",
  playerStatKeys: "",
};

export default function TheoryBetsEdaPage() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [rows, setRows] = useState<EDAGameRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const summary = useMemo(() => {
    if (!rows.length) {
      return {
        sampleSize: 0,
        homeWinRate: null as number | null,
        homeCoverRate: null as number | null,
        overRate: null as number | null,
      };
    }

    let homeWins = 0;
    let homeCovers = 0;
    let totalOver = 0;
    let totalWithCoverTarget = 0;
    let totalWithTotalTarget = 0;

    for (const row of rows) {
      const t = row.targets;
      if (t.winner === "home") homeWins += 1;
      if (t.did_home_cover !== null && t.did_home_cover !== undefined) {
        totalWithCoverTarget += 1;
        if (t.did_home_cover) homeCovers += 1;
      }
      if (t.total_result) {
        totalWithTotalTarget += 1;
        if (t.total_result === "over") totalOver += 1;
      }
    }

    const sampleSize = rows.length;
    return {
      sampleSize,
      homeWinRate: sampleSize ? homeWins / sampleSize : null,
      homeCoverRate: totalWithCoverTarget ? homeCovers / totalWithCoverTarget : null,
      overRate: totalWithTotalTarget ? totalOver / totalWithTotalTarget : null,
    };
  }, [rows]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload: EDAFilters = {
        leagueCode: form.leagueCode,
        season: form.season ? Number(form.season) : undefined,
        startDate: form.startDate || undefined,
        endDate: form.endDate || undefined,
        team: form.team || undefined,
        seasonType: form.seasonType || undefined,
        marketType: form.marketType || undefined,
        side: form.side || undefined,
        closingOnly: form.closingOnly,
        includePlayerStats: form.includePlayerStats,
        teamStatKeys: form.teamStatKeys
          ? form.teamStatKeys.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        playerStatKeys: form.playerStatKeys
          ? form.playerStatKeys.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        limit: 200,
        offset: 0,
      };

      const response = await runEdaQuery(payload);
      setRows(response.rows);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setForm(INITIAL_FORM);
    setRows([]);
    setTotal(0);
    setError(null);
  };

  const renderWinnerPill = (row: EDAGameRow) => {
    const winner = row.targets.winner;
    let label = "Unknown";
    let className = `${styles.pill} ${styles.pillUnknown}`;
    if (winner === "home") {
      label = "Home";
      className = `${styles.pill} ${styles.pillWin}`;
    } else if (winner === "away") {
      label = "Away";
      className = `${styles.pill} ${styles.pillLoss}`;
    } else if (winner === "tie") {
      label = "Tie";
      className = `${styles.pill} ${styles.pillPush}`;
    }
    return <span className={className}>{label}</span>;
  };

  const renderCoverPill = (row: EDAGameRow) => {
    const value = row.targets.did_home_cover;
    if (value === null || value === undefined) {
      return <span className={`${styles.pill} ${styles.pillUnknown}`}>N/A</span>;
    }
    return (
      <span className={`${styles.pill} ${value ? styles.pillWin : styles.pillLoss}`}>
        {value ? "Home cover" : "No cover"}
      </span>
    );
  };

  const renderTotalPill = (row: EDAGameRow) => {
    const value = row.targets.total_result;
    if (!value) {
      return <span className={`${styles.pill} ${styles.pillUnknown}`}>N/A</span>;
    }
    let className = styles.pillPush;
    if (value === "over") className = styles.pillWin;
    if (value === "under") className = styles.pillLoss;
    return <span className={`${styles.pill} ${className}`}>{value}</span>;
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
        <form onSubmit={handleSubmit}>
          <div className={styles.formGrid}>
            <div className={styles.field}>
              <label className={styles.label}>League</label>
              <select
                className={styles.select}
                value={form.leagueCode}
                onChange={(e) => setForm((prev) => ({ ...prev, leagueCode: e.target.value as LeagueCode }))}
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

            <div className={styles.field}>
              <label className={styles.label}>Team stat keys (comma separated)</label>
              <input
                className={styles.input}
                type="text"
                placeholder="points,rebound,total_yards..."
                value={form.teamStatKeys}
                onChange={(e) => setForm((prev) => ({ ...prev, teamStatKeys: e.target.value }))}
              />
              <p className={styles.hint}>Leave blank to include all team stats.</p>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Player stat keys (comma separated)</label>
              <input
                className={styles.input}
                type="text"
                placeholder="minutes,points,rebounds..."
                value={form.playerStatKeys}
                onChange={(e) => setForm((prev) => ({ ...prev, playerStatKeys: e.target.value }))}
              />
              <p className={styles.hint}>Only used when including player stats.</p>
            </div>
          </div>

          <div className={styles.toggleRow}>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={form.closingOnly}
                onChange={(e) => setForm((prev) => ({ ...prev, closingOnly: e.target.checked }))}
              />
              Closing lines only
            </label>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={form.includePlayerStats}
                onChange={(e) => setForm((prev) => ({ ...prev, includePlayerStats: e.target.checked }))}
              />
              Include player-level stats
            </label>
          </div>

          <div className={styles.actions}>
            <button type="submit" className={styles.primaryButton} disabled={loading}>
              {loading ? "Running query..." : "Run EDA query"}
            </button>
            <button type="button" className={styles.secondaryButton} onClick={handleReset} disabled={loading}>
              Reset
            </button>
          </div>

          {error && <div className={styles.error}>{error}</div>}
        </form>
      </AdminCard>

      <AdminCard>
        <div className={styles.header}>
          <h2 className={styles.title}>Results</h2>
          <p className={styles.subtitle}>
            {rows.length
              ? `Showing ${rows.length.toLocaleString()} of ${total.toLocaleString()} games`
              : "Run a query to see games and outcome targets."}
          </p>
        </div>

        {loading && rows.length === 0 && <LoadingState message="Loading EDA results..." />}
        {!loading && !rows.length && !error && (
          <p className={styles.emptyState}>No games match the current filters.</p>
        )}
        {rows.length > 0 && (
          <>
            <div className={styles.summaryRow}>
              <span>
                Sample size: <span className={styles.summaryValue}>{summary.sampleSize.toLocaleString()}</span>
              </span>
              {summary.homeWinRate !== null && (
                <span>
                  Home win rate:{" "}
                  <span className={styles.summaryValue}>{(summary.homeWinRate * 100).toFixed(1)}%</span>
                </span>
              )}
              {summary.homeCoverRate !== null && (
                <span>
                  Home cover rate:{" "}
                  <span className={styles.summaryValue}>{(summary.homeCoverRate * 100).toFixed(1)}%</span>
                </span>
              )}
              {summary.overRate !== null && (
                <span>
                  Over rate:{" "}
                  <span className={styles.summaryValue}>{(summary.overRate * 100).toFixed(1)}%</span>
                </span>
              )}
            </div>

            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>League</th>
                    <th>Matchup</th>
                    <th>Score</th>
                    <th>Winner</th>
                    <th>Cover</th>
                    <th>Total</th>
                    <th>Margin</th>
                    <th>Combined</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.game_id}>
                      <td>{new Date(row.game_date).toLocaleDateString()}</td>
                      <td>{row.league_code}</td>
                      <td>
                        {row.away_team} @ {row.home_team}
                      </td>
                      <td>
                        {row.away_score ?? "—"} - {row.home_score ?? "—"}
                      </td>
                      <td>{renderWinnerPill(row)}</td>
                      <td>{renderCoverPill(row)}</td>
                      <td>{renderTotalPill(row)}</td>
                      <td>{row.targets.margin_of_victory ?? "—"}</td>
                      <td>{row.targets.combined_score ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {loading && rows.length > 0 && <LoadingState message="Updating results..." />}
        {error && <ErrorState error={new Error(error)} title="Unable to run EDA query" />}
      </AdminCard>
    </div>
  );
}



