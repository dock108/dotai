"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./styles.module.css";
import { createScrapeRun, listScrapeRuns, type ScrapeRunResponse } from "@/lib/api/sportsAdmin";
import { getFullSeasonDates, shouldAutoFillDates, type LeagueCode } from "@/lib/utils/seasonDates";
import { SUPPORTED_LEAGUES, SCRAPE_RUN_STATUS_COLORS, DEFAULT_SCRAPE_RUN_FORM } from "@/lib/constants/sports";
import { formatDateTime } from "@/lib/utils/dateFormat";
import { useScrapeRuns } from "@/lib/hooks/useScrapeRuns";

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
  const { runs, loading, error: runsError, refetch: fetchRuns } = useScrapeRuns();
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [form, setForm] = useState(DEFAULT_SCRAPE_RUN_FORM);
  
  // Use runsError if no local error
  const displayError = error || runsError;

  useEffect(() => {
    if (shouldAutoFillDates(form.leagueCode as LeagueCode, form.season, form.startDate, form.endDate)) {
      const seasonYear = Number(form.season);
      if (!isNaN(seasonYear) && seasonYear >= 2000 && seasonYear <= 2100) {
        const dates = getFullSeasonDates(form.leagueCode as LeagueCode, seasonYear);
        setForm((prev) => ({
          ...prev,
          startDate: dates.startDate,
          endDate: dates.endDate,
        }));
      }
    }
  }, [form.leagueCode, form.season]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const startDate = form.startDate?.trim() || undefined;
      const endDate = form.endDate?.trim() || undefined;
      
      if (startDate && !/^\d{4}-\d{2}-\d{2}$/.test(startDate)) {
        throw new Error(`Invalid start date format: ${startDate}. Expected YYYY-MM-DD`);
      }
      if (endDate && !/^\d{4}-\d{2}-\d{2}$/.test(endDate)) {
        throw new Error(`Invalid end date format: ${endDate}. Expected YYYY-MM-DD`);
      }
      
      const result = await createScrapeRun({
        requestedBy: form.requestedBy,
        config: {
          leagueCode: form.leagueCode,
          season: form.season ? Number(form.season) : undefined,
          startDate: startDate,
          endDate: endDate,
          includeBoxscores: form.includeBoxscores,
          includeOdds: form.includeOdds,
          backfillPlayerStats: form.backfillPlayerStats,
          backfillOdds: form.backfillOdds,
        },
      });
      setSuccess(`Scrape run #${result.id} scheduled successfully!`);
      fetchRuns();
      setForm(DEFAULT_SCRAPE_RUN_FORM);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
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
        {success && <p className={styles.success}>{success}</p>}
        {displayError && <p className={styles.error}>{displayError}</p>}
        <form className={styles.form} onSubmit={handleSubmit}>
          <label>
            League
            <select
              value={form.leagueCode}
              onChange={(e) => setForm((prev) => ({ ...prev, leagueCode: e.target.value as LeagueCode }))}
            >
              {SUPPORTED_LEAGUES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>

          <label>
            Season (optional - auto-fills dates if provided)
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
          {form.season && !form.startDate && !form.endDate && (
            <p className={styles.hint}>
              Dates will be auto-filled for the full {form.season} season (including playoffs/championships)
            </p>
          )}

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

          <div className={styles.toggles}>
            <label>
              <input
                type="checkbox"
                checked={form.backfillPlayerStats}
                onChange={(e) => setForm((prev) => ({ ...prev, backfillPlayerStats: e.target.checked }))}
              />
              Backfill missing player stats
            </label>
            <label>
              <input
                type="checkbox"
                checked={form.backfillOdds}
                onChange={(e) => setForm((prev) => ({ ...prev, backfillOdds: e.target.checked }))}
              />
              Backfill missing odds
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
                  <Link href={`/admin/ingestion/${run.id}`}>{run.id}</Link>
                </td>
                <td>{run.league_code}</td>
                <td>
                  <span
                    className={styles.statusPill}
                    style={{ backgroundColor: SCRAPE_RUN_STATUS_COLORS[run.status] ?? "#5f6368" }}
                  >
                    {run.status}
                  </span>
                </td>
                <td>{run.season ?? "—"}</td>
                <td>
                  {run.start_date || run.end_date
                    ? `${run.start_date ?? "?"} to ${run.end_date ?? "?"}`
                    : "—"}
                </td>
                <td>{run.summary ?? "—"}</td>
                <td>{formatDateTime(run.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

