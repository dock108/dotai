"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";
import { LoadingSpinner, ErrorDisplay } from "@dock108/ui-kit";
import { GameSummary, GameFilters, listGames } from "@/lib/api/sportsAdmin";

const LEAGUE_OPTIONS = ["NBA", "NCAAB", "NFL", "NCAAF", "MLB", "NHL"];

const DEFAULT_FILTERS: GameFilters = {
  leagues: [],
  season: undefined,
  team: "",
  startDate: undefined,
  endDate: undefined,
  missingBoxscore: false,
  missingPlayerStats: false,
  missingOdds: false,
  missingAny: false,
  limit: 50,
  offset: 0,
};

/**
 * Boxscore admin page - comprehensive game browser with advanced filtering.
 * 
 * Provides a rich interface for browsing ingested sports games with:
 * - Multi-league filtering and date range selection
 * - Team name search
 * - Missing data filters (boxscores, player stats, odds)
 * - Pagination with "load more" functionality
 * - Completeness indicators and summary statistics
 * 
 * Clicking a game navigates to the detailed game view with tabs for
 * team stats, player stats, odds, derived metrics, and raw payloads.
 */
export default function BoxscoreAdminPage() {
  const [formFilters, setFormFilters] = useState<GameFilters>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<GameFilters>(DEFAULT_FILTERS);
  const [games, setGames] = useState<GameSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await listGames(appliedFilters);
        if (cancelled) return;
        setGames((prev) =>
          appliedFilters.offset && appliedFilters.offset > 0 ? [...prev, ...response.games] : response.games,
        );
        setTotal(response.total);
        setNextOffset(response.next_offset);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load games");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [appliedFilters]);

  const completenessSummary = useMemo(() => {
    const ready = games.filter((g) => g.has_required_data).length;
    return `${ready}/${games.length} games ready`;
  }, [games]);

  const handleLeagueToggle = (code: string) => {
    setFormFilters((prev) => {
      const exists = prev.leagues.includes(code);
      return {
        ...prev,
        leagues: exists ? prev.leagues.filter((lg) => lg !== code) : [...prev.leagues, code],
      };
    });
  };

  const handleApply = () => {
    setAppliedFilters({ ...formFilters, offset: 0 });
  };

  const handleReset = () => {
    setFormFilters(DEFAULT_FILTERS);
    setAppliedFilters(DEFAULT_FILTERS);
  };

  const handleLoadMore = () => {
    if (nextOffset === null) return;
    setAppliedFilters({ ...appliedFilters, offset: nextOffset });
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Admin</p>
          <h1>Boxscore Viewer</h1>
          <p className={styles.subtitle}>Validate scraped data before it powers the Theory Engine.</p>
        </div>
        <div className={styles.metrics}>
          <span>Total Games: {total}</span>
          <span>{completenessSummary}</span>
        </div>
      </div>

      <section className={styles.filtersCard}>
        <div className={styles.filtersGrid}>
          <div>
            <label>League</label>
            <div className={styles.leagueChips}>
              {LEAGUE_OPTIONS.map((code) => (
                <button
                  key={code}
                  type="button"
                  className={`${styles.chip} ${
                    formFilters.leagues.includes(code) ? styles.chipActive : ""
                  }`}
                  onClick={() => handleLeagueToggle(code)}
                >
                  {code}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label>Season</label>
            <input
              type="number"
              placeholder="2024"
              value={formFilters.season ?? ""}
              onChange={(e) =>
                setFormFilters((prev) => ({
                  ...prev,
                  season: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            />
          </div>
          <div>
            <label>Team</label>
            <input
              type="text"
              placeholder="Lakers, Purdue, etc."
              value={formFilters.team ?? ""}
              onChange={(e) => setFormFilters((prev) => ({ ...prev, team: e.target.value }))}
            />
          </div>
          <div className={styles.dates}>
            <label>Date Range</label>
            <div className={styles.dateInputs}>
              <input
                type="date"
                value={formFilters.startDate ?? ""}
                onChange={(e) => setFormFilters((prev) => ({ ...prev, startDate: e.target.value || undefined }))}
              />
              <span>→</span>
              <input
                type="date"
                value={formFilters.endDate ?? ""}
                onChange={(e) => setFormFilters((prev) => ({ ...prev, endDate: e.target.value || undefined }))}
              />
            </div>
          </div>
          <div className={styles.missingToggles}>
            <label>Missing Data</label>
            <div className={styles.toggleList}>
              <label>
                <input
                  type="checkbox"
                  checked={formFilters.missingBoxscore ?? false}
                  onChange={(e) => setFormFilters((prev) => ({ ...prev, missingBoxscore: e.target.checked }))}
                />
                Boxscore
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={formFilters.missingPlayerStats ?? false}
                  onChange={(e) => setFormFilters((prev) => ({ ...prev, missingPlayerStats: e.target.checked }))}
                />
                Player stats
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={formFilters.missingOdds ?? false}
                  onChange={(e) => setFormFilters((prev) => ({ ...prev, missingOdds: e.target.checked }))}
                />
                Odds
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={formFilters.missingAny ?? false}
                  onChange={(e) => setFormFilters((prev) => ({ ...prev, missingAny: e.target.checked }))}
                />
                Any required
              </label>
            </div>
          </div>
        </div>
        <div className={styles.filterActions}>
          <button type="button" className={styles.secondaryButton} onClick={handleReset}>
            Reset
          </button>
          <button type="button" className={styles.primaryButton} onClick={handleApply}>
            Apply Filters
          </button>
        </div>
      </section>

      {error ? (
        <ErrorDisplay error={new Error(error)} title="Unable to load games" />
      ) : (
        <section className={styles.tableCard}>
          <div className={styles.tableHeader}>
            <h2>Recent Games</h2>
            <span>{games.length ? `${games.length} shown` : "No games found"}</span>
          </div>
          {loading && games.length === 0 ? (
            <LoadingSpinner message="Loading games..." />
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>League</th>
                    <th>Matchup</th>
                    <th>Score</th>
                    <th>Data</th>
                    <th>Scrape</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((game) => (
                    <tr key={game.id}>
                      <td>{new Date(game.game_date).toLocaleDateString()}</td>
                      <td>{game.league_code}</td>
                      <td className={styles.matchupCell}>
                        <span>{game.away_team}</span>
                        <span>@</span>
                        <span>{game.home_team}</span>
                      </td>
                      <td>
                        {game.away_score ?? "-"} &nbsp;–&nbsp; {game.home_score ?? "-"}
                      </td>
                      <td>
                        <span className={`${styles.badge} ${game.has_boxscore ? styles.badgeOk : styles.badgeWarn}`}>
                          BX
                        </span>
                        <span
                          className={`${styles.badge} ${game.has_player_stats ? styles.badgeOk : styles.badgeWarn}`}
                        >
                          PS
                        </span>
                        <span className={`${styles.badge} ${game.has_odds ? styles.badgeOk : styles.badgeWarn}`}>
                          OD
                        </span>
                      </td>
                      <td>
                        <div className={styles.metaColumn}>
                          <span>v{game.scrape_version ?? "-"}</span>
                          <span className={styles.metaSecondary}>
                            {game.last_scraped_at ? new Date(game.last_scraped_at).toLocaleString() : "—"}
                          </span>
                        </div>
                      </td>
                      <td>
                        <Link href={`/admin/boxscores/${game.id}`} className={styles.linkButton}>
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {!games.length && !loading && (
                    <tr>
                      <td colSpan={7} className={styles.emptyState}>
                        No games found with the current filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
          {loading && games.length > 0 && <LoadingSpinner message="Updating list..." />}
          {nextOffset !== null && !loading && (
            <div className={styles.loadMoreRow}>
              <button type="button" onClick={handleLoadMore} className={styles.primaryButton}>
                Load more
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

