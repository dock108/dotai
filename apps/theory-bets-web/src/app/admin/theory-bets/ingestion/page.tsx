"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./styles.module.css";
import { createScrapeRun, listScrapeRuns, type ScrapeRunResponse } from "@/lib/api/sportsAdmin";

const LEAGUES = ["NBA", "NCAAB", "NFL", "NCAAF", "MLB", "NHL"];
const STATUS_COLORS: Record<string, string> = {
  success: "#0f9d58",
  running: "#fbbc04",
  pending: "#5f6368",
  error: "#ea4335",
};

/**
 * Sports data ingestion admin page.
 * 
 * Allows administrators to:
 * - Configure scrape runs (league, season, date range, boxscores/odds)
 * - Monitor scrape run status and results
 * - View scrape run history and summaries
 * 
 * Scrape runs are executed by the theory-bets-scraper Celery workers
 * via the theory-engine-api backend.
 */
export default function IngestionAdminPage() {
  const [runs, setRuns] = useState<ScrapeRunResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    leagueCode: "NBA",
    season: "",
    startDate: "",
    endDate: "",
    includeBoxscores: true,
    includeOdds: true,
    requestedBy: "admin@dock108.ai",
  });

  const fetchRuns = async () => {
    try {
      setLoading(true);
      const data = await listScrapeRuns();
      setRuns(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);
    try {
      await createScrapeRun({
        requestedBy: form.requestedBy,
        config: {
          leagueCode: form.leagueCode,
          season: form.season ? Number(form.season) : undefined,
          startDate: form.startDate || undefined,
          endDate: form.endDate || undefined,
          includeBoxscores: form.includeBoxscores,
          includeOdds: form.includeOdds,
        },
      });
      await fetchRuns();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  };

  const latestRuns = useMemo(() => runs.slice(0, 25), [runs]);

  return (
    <div className={styles.container}>
      <h1>Sports Data Ingestion</h1>
      <p className={styles.subtitle}>Configure and monitor boxscore + odds scrapes.</p>

      <section className={styles.card}>
        <h2>Create Scrape Run</h2>
        <form className={styles.form} onSubmit={handleSubmit}>
          <label>
            League
            <select
              value={form.leagueCode}
              onChange={(e) => setForm((prev) => ({ ...prev, leagueCode: e.target.value }))}
            >
              {LEAGUES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>

          <label>
            Season (optional)
            <input
              type="number"
              value={form.season}
              onChange={(e) => setForm((prev) => ({ ...prev, season: e.target.value }))}
              placeholder="2024"
            />
          </label>

          <div className={styles.row}>
            <label>
              Start date
              <input
                type="date"
                value={form.startDate}
                onChange={(e) => setForm((prev) => ({ ...prev, startDate: e.target.value }))}
              />
            </label>
            <label>
              End date
              <input
                type="date"
                value={form.endDate}
                onChange={(e) => setForm((prev) => ({ ...prev, endDate: e.target.value }))}
              />
            </label>
          </div>

          <div className={styles.toggles}>
            <label>
              <input
                type="checkbox"
                checked={form.includeBoxscores}
                onChange={(e) => setForm((prev) => ({ ...prev, includeBoxscores: e.target.checked }))}
              />
              Include boxscores
            </label>
            <label>
              <input
                type="checkbox"
                checked={form.includeOdds}
                onChange={(e) => setForm((prev) => ({ ...prev, includeOdds: e.target.checked }))}
              />
              Include odds
            </label>
          </div>

          <button type="submit" disabled={creating}>
            {creating ? "Scheduling..." : "Schedule Run"}
          </button>
        </form>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <h2>Recent Runs</h2>
          <button onClick={fetchRuns} disabled={loading}>
            Refresh
          </button>
        </div>
        {error && <p className={styles.error}>{error}</p>}
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID</th>
              <th>League</th>
              <th>Status</th>
              <th>Season</th>
              <th>Date range</th>
              <th>Summary</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {latestRuns.map((run) => (
              <tr key={run.id}>
                <td>
                  <Link href={`/admin/theory-bets/ingestion/${run.id}`}>{run.id}</Link>
                </td>
                <td>{run.league_code}</td>
                <td>
                  <span
                    className={styles.statusPill}
                    style={{ backgroundColor: STATUS_COLORS[run.status] ?? "#5f6368" }}
                  >
                    {run.status}
                  </span>
                </td>
                <td>{run.season ?? "—"}</td>
                <td>
                  {run.start_date || run.end_date
                    ? `${run.start_date ?? "?"} → ${run.end_date ?? "?"}`
                    : "—"}
                </td>
                <td>{run.summary ?? "—"}</td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

