"use client";

import { useMemo } from "react";
import styles from "./page.module.css";
import { useGameFilters } from "@/lib/hooks/useGameFilters";
import { GameFiltersForm } from "@/components/admin/GameFiltersForm";
import { GamesTable } from "@/components/admin/GamesTable";
import { getQuickDateRange } from "@/lib/utils/dateFormat";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

/**
 * Games admin page - comprehensive game browser with advanced filtering and pagination.
 */
export default function GamesAdminPage() {
  const {
    formFilters,
    setFormFilters,
    appliedFilters,
    games,
    total,
    loading,
    error,
    applyFilters,
    resetFilters,
  } = useGameFilters({ defaultLimit: 25 });

  const currentPage = Math.floor((appliedFilters.offset || 0) / (appliedFilters.limit || 25)) + 1;
  const totalPages = Math.ceil(total / (appliedFilters.limit || 25));
  const startItem = (appliedFilters.offset || 0) + 1;
  const endItem = Math.min((appliedFilters.offset || 0) + (appliedFilters.limit || 25), total);

  const handlePageChange = (newPage: number) => {
    const limit = appliedFilters.limit || 25;
    const newOffset = (newPage - 1) * limit;
    setFormFilters((prev) => ({ ...prev, offset: newOffset }));
    applyFilters();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handlePageSizeChange = (newSize: number) => {
    setFormFilters((prev) => ({ ...prev, limit: newSize, offset: 0 }));
    applyFilters();
  };

  const handleQuickDateRange = (days: number) => {
    const { startDate, endDate } = getQuickDateRange(days);
    setFormFilters((prev) => ({ ...prev, startDate, endDate }));
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

      <GameFiltersForm
        filters={formFilters}
        onFiltersChange={setFormFilters}
        onApply={applyFilters}
        onReset={resetFilters}
        onQuickDateRange={handleQuickDateRange}
      />

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

      {error && <div className={styles.error}>{error}</div>}

      {loading && games.length === 0 && <div className={styles.loading}>Loading...</div>}

      {games.length > 0 && <GamesTable games={games} detailLinkPrefix="/admin/games" showCompleteness={false} />}

      {!loading && games.length === 0 && !error && (
        <div className={styles.empty}>No games found. Try adjusting your filters.</div>
      )}
    </div>
  );
}
