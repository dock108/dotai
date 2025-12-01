"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";
import { GameSummary, GameFilters, listGames } from "@/lib/api/sportsAdmin";
import { SUPPORTED_LEAGUES } from "@/lib/constants/sports";
import { getQuickDateRange, formatDate } from "@/lib/utils/dateFormat";

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
  limit: 25,
  offset: 0,
};

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

/**
 * Games admin page - comprehensive game browser with advanced filtering.
 */
export default function GamesAdminPage() {
  const [formFilters, setFormFilters] = useState<GameFilters>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<GameFilters>(DEFAULT_FILTERS);
  const [games, setGames] = useState<GameSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Calculate current page from offset
  const currentPage = Math.floor((appliedFilters.offset || 0) / (appliedFilters.limit || 25)) + 1;
  const totalPages = Math.ceil(total / (appliedFilters.limit || 25));
  const startItem = (appliedFilters.offset || 0) + 1;
  const endItem = Math.min((appliedFilters.offset || 0) + (appliedFilters.limit || 25), total);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await listGames(appliedFilters);
        if (cancelled) return;
        if (appliedFilters.offset === 0) {
          setGames(response.games);
        } else {
          setGames((prev) => [...prev, ...response.games]);
        }
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
    return () => { cancelled = true; };
  }, [appliedFilters]);

  const handleApplyFilters = () => {
    setAppliedFilters({ ...formFilters, offset: 0 });
    setGames([]);
  };

  const handlePageChange = (newPage: number) => {
    const limit = appliedFilters.limit || 25;
    const newOffset = (newPage - 1) * limit;
    setAppliedFilters((prev) => ({ ...prev, offset: newOffset }));
    setGames([]);
    // Scroll to top of table
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePageSizeChange = (newSize: number) => {
    setFormFilters((prev) => ({ ...prev, limit: newSize }));
    setAppliedFilters((prev) => ({ ...prev, limit: newSize, offset: 0 }));
    setGames([]);
  };

  const setQuickDateRange = (days: number) => {
    const { startDate, endDate } = getQuickDateRange(days);
    setFormFilters((prev) => ({
      ...prev,
      startDate,
      endDate,
    }));
  };

  const toggleLeague = (lg: string) => {
    setFormFilters((prev) => ({
      ...prev,
      leagues: prev.leagues.includes(lg)
        ? prev.leagues.filter((l) => l !== lg)
        : [...prev.leagues, lg],
    }));
  };

  const stats = useMemo(() => {
    const withBoxscore = games.filter((g) => g.has_boxscore).length;
    const withPlayerStats = games.filter((g) => g.has_player_stats).length;
    const withOdds = games.filter((g) => g.has_odds).length;
    return { withBoxscore, withPlayerStats, withOdds, total: games.length };
  }, [games]);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Games</h1>
        <p className={styles.subtitle}>Browse ingested games with boxscores and odds</p>
      </header>

      {/* Filters */}
      <div className={styles.filtersCard}>
        <div className={styles.filterSection}>
          <div className={styles.filterLabel}>Leagues</div>
          <div className={styles.leagueChips}>
            {SUPPORTED_LEAGUES.map((lg) => (
              <button
                key={lg}
                type="button"
                className={`${styles.chip} ${formFilters.leagues.includes(lg) ? styles.chipActive : ""}`}
                onClick={() => toggleLeague(lg)}
              >
                {lg}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.filterRow}>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Season</label>
            <input
              type="number"
              className={styles.input}
              placeholder="e.g. 2024"
              value={formFilters.season ?? ""}
              onChange={(e) =>
                setFormFilters((prev) => ({
                  ...prev,
                  season: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            />
          </div>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Team</label>
            <input
              type="text"
              className={styles.input}
              placeholder="Team name..."
              value={formFilters.team ?? ""}
              onChange={(e) =>
                setFormFilters((prev) => ({ ...prev, team: e.target.value }))
              }
            />
          </div>
        </div>

        {/* Date Range Section */}
        <div className={styles.filterSection}>
          <div className={styles.filterLabel}>Date Range</div>
          <div className={styles.quickDateButtons}>
            <button
              type="button"
              className={styles.quickDateButton}
              onClick={() => setQuickDateRange(0)}
            >
              Today
            </button>
            <button
              type="button"
              className={styles.quickDateButton}
              onClick={() => setQuickDateRange(7)}
            >
              Last 7 Days
            </button>
            <button
              type="button"
              className={styles.quickDateButton}
              onClick={() => setQuickDateRange(30)}
            >
              Last 30 Days
            </button>
            <button
              type="button"
              className={styles.quickDateButton}
              onClick={() => {
                setFormFilters((prev) => ({ ...prev, startDate: undefined, endDate: undefined }));
              }}
            >
              Clear Dates
            </button>
          </div>
          <div className={styles.filterRow}>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Start Date</label>
              <input
                type="date"
                className={styles.input}
                value={formFilters.startDate ?? ""}
                onChange={(e) =>
                  setFormFilters((prev) => ({ ...prev, startDate: e.target.value || undefined }))
                }
              />
            </div>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>End Date</label>
              <input
                type="date"
                className={styles.input}
                value={formFilters.endDate ?? ""}
                onChange={(e) =>
                  setFormFilters((prev) => ({ ...prev, endDate: e.target.value || undefined }))
                }
              />
            </div>
          </div>
        </div>

        <div className={styles.filterRow}>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={formFilters.missingBoxscore ?? false}
              onChange={(e) =>
                setFormFilters((prev) => ({ ...prev, missingBoxscore: e.target.checked }))
              }
            />
            Missing Boxscore
          </label>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={formFilters.missingPlayerStats ?? false}
              onChange={(e) =>
                setFormFilters((prev) => ({ ...prev, missingPlayerStats: e.target.checked }))
              }
            />
            Missing Player Stats
          </label>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={formFilters.missingOdds ?? false}
              onChange={(e) =>
                setFormFilters((prev) => ({ ...prev, missingOdds: e.target.checked }))
              }
            />
            Missing Odds
          </label>
        </div>

        <button className={styles.applyButton} onClick={handleApplyFilters}>
          Apply Filters
        </button>
      </div>

      {/* Stats and Pagination Info */}
      <div className={styles.statsRow}>
        <div className={styles.stat}>
          <span className={styles.statValue}>{total.toLocaleString()}</span>
          <span className={styles.statLabel}>Total Games</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statValue}>{stats.withBoxscore}</span>
          <span className={styles.statLabel}>Boxscores</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statValue}>{stats.withPlayerStats}</span>
          <span className={styles.statLabel}>Player Stats</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statValue}>{stats.withOdds}</span>
          <span className={styles.statLabel}>Odds</span>
        </div>
      </div>

      {/* Pagination Controls */}
      {total > 0 && (
        <div className={styles.paginationControls}>
          <div className={styles.paginationInfo}>
            Showing {startItem.toLocaleString()} - {endItem.toLocaleString()} of {total.toLocaleString()} games
          </div>
          <div className={styles.paginationRight}>
            <label className={styles.pageSizeLabel}>
              Page size:
              <select
                className={styles.pageSizeSelect}
                value={appliedFilters.limit || 25}
                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </label>
            <div className={styles.paginationButtons}>
              <button
                className={styles.paginationButton}
                onClick={() => handlePageChange(1)}
                disabled={currentPage === 1 || loading}
              >
                First
              </button>
              <button
                className={styles.paginationButton}
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1 || loading}
              >
                Previous
              </button>
              <span className={styles.pageInfo}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                className={styles.paginationButton}
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage >= totalPages || loading}
              >
                Next
              </button>
              <button
                className={styles.paginationButton}
                onClick={() => handlePageChange(totalPages)}
                disabled={currentPage >= totalPages || loading}
              >
                Last
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && <div className={styles.error}>{error}</div>}

      {/* Games List */}
      {games.length > 0 && (
        <div className={styles.gamesTable}>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>League</th>
                <th>Matchup</th>
                <th>Score</th>
                <th>Data</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {games.map((game) => (
                <tr key={game.id}>
                  <td>{formatDate(game.game_date)}</td>
                  <td><span className={styles.leagueBadge}>{game.league_code}</span></td>
                  <td>
                    {game.away_team} @ {game.home_team}
                  </td>
                  <td>
                    {game.away_score ?? "-"} - {game.home_score ?? "-"}
                  </td>
                  <td>
                    <span className={`${styles.indicator} ${game.has_boxscore ? styles.indicatorGreen : styles.indicatorRed}`} title="Boxscore">B</span>
                    <span className={`${styles.indicator} ${game.has_player_stats ? styles.indicatorGreen : styles.indicatorRed}`} title="Player Stats">P</span>
                    <span className={`${styles.indicator} ${game.has_odds ? styles.indicatorGreen : styles.indicatorRed}`} title="Odds">O</span>
                  </td>
                  <td>
                    <Link href={`/admin/games/${game.id}`} className={styles.viewLink}>
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Loading */}
      {loading && <div className={styles.loading}>Loading...</div>}


      {/* Empty State */}
      {!loading && games.length === 0 && !error && (
        <div className={styles.empty}>No games found. Try adjusting your filters.</div>
      )}
    </div>
  );
}

