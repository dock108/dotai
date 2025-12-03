"use client";

import { useMemo } from "react";
import Link from "next/link";
import styles from "./page.module.css";
import { LoadingSpinner, ErrorDisplay } from "@dock108/ui-kit";
import { useGameFilters } from "@/lib/hooks/useGameFilters";
import { GameFiltersForm } from "@/components/admin/GameFiltersForm";
import { GamesTable } from "@/components/admin/GamesTable";

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
  const {
    formFilters,
    setFormFilters,
    appliedFilters,
    games,
    total,
    nextOffset,
    loading,
    error,
    applyFilters,
    resetFilters,
    loadMore,
  } = useGameFilters({ defaultLimit: 50, loadMoreMode: true });

  const completenessSummary = useMemo(() => {
    const ready = games.filter((g) => g.has_required_data).length;
    return `${ready}/${games.length} games ready`;
  }, [games]);

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

      <GameFiltersForm
        filters={formFilters}
        onFiltersChange={setFormFilters}
        onApply={applyFilters}
        onReset={resetFilters}
      />

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
            <GamesTable games={games} detailLinkPrefix="/admin/games" showCompleteness={true} />
          )}
          {loading && games.length > 0 && <LoadingSpinner message="Updating list..." />}
          {nextOffset !== null && !loading && (
            <div className={styles.loadMoreRow}>
              <button type="button" onClick={loadMore} className={styles.primaryButton}>
                Load more
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

