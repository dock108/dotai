"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";
import { GameSummary, GameFilters, listGames } from "@/lib/api/sportsAdmin";
import { SUPPORTED_LEAGUES } from "@/lib/constants/sports";

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

  const handleLoadMore = () => {
    if (nextOffset !== null) {
      setAppliedFilters((prev) => ({ ...prev, offset: nextOffset }));
    }
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

      {/* Stats */}
      <div className={styles.statsRow}>
        <div className={styles.stat}>
          <span className={styles.statValue}>{total}</span>
          <span className={styles.statLabel}>Total</span>
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
                  <td>{new Date(game.game_date).toLocaleDateString()}</td>
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

      {/* Load More */}
      {!loading && nextOffset !== null && (
        <button className={styles.loadMoreButton} onClick={handleLoadMore}>
          Load More
        </button>
      )}

      {/* Empty State */}
      {!loading && games.length === 0 && !error && (
        <div className={styles.empty}>No games found. Try adjusting your filters.</div>
      )}
    </div>
  );
}

