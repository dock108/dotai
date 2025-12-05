"use client";

import Link from "next/link";
import { useMemo } from "react";
import { type GameSummary } from "@/lib/api/sportsAdmin";
import styles from "./GamesTable.module.css";

interface GamesTableProps {
  games: GameSummary[];
  detailLinkPrefix?: string;
  showCompleteness?: boolean;
}

/**
 * Table component for displaying game summaries.
 * Shows game metadata, scores, and data completeness indicators.
 */
export function GamesTable({ games, detailLinkPrefix = "/admin/theory-bets/games", showCompleteness = true }: GamesTableProps) {
  const stats = useMemo(() => {
    const withBoxscore = games.filter((g) => g.has_boxscore).length;
    const withPlayerStats = games.filter((g) => g.has_player_stats).length;
    const withOdds = games.filter((g) => g.has_odds).length;
    const ready = games.filter((g) => g.has_required_data).length;
    return { withBoxscore, withPlayerStats, withOdds, ready, total: games.length };
  }, [games]);

  return (
    <>
      {showCompleteness && games.length > 0 && (
        <div className={styles.statsBar}>
          <span>Boxscores: {stats.withBoxscore}/{stats.total}</span>
          <span>Player Stats: {stats.withPlayerStats}/{stats.total}</span>
          <span>Odds: {stats.withOdds}/{stats.total}</span>
          <span>Ready: {stats.ready}/{stats.total}</span>
        </div>
      )}

      <table className={styles.table}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Date</th>
            <th>League</th>
            <th>Teams</th>
            <th>Score</th>
            {showCompleteness && (
              <>
                <th>Boxscore</th>
                <th>Players</th>
                <th>Odds</th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {games.length === 0 ? (
            <tr>
              <td colSpan={showCompleteness ? 8 : 5} className={styles.emptyCell}>
                No games found
              </td>
            </tr>
          ) : (
            games.map((game) => (
              <tr key={game.id}>
                <td>
                  <Link href={`${detailLinkPrefix}/${game.id}`} className={styles.link}>
                    {game.id}
                  </Link>
                </td>
                <td>{new Date(game.game_date).toLocaleDateString()}</td>
                <td>{game.league_code}</td>
                <td>
                  {game.away_team} @ {game.home_team}
                </td>
                <td>
                  {game.away_score !== null && game.home_score !== null
                    ? `${game.away_score} - ${game.home_score}`
                    : "—"}
                </td>
                {showCompleteness && (
                  <>
                    <td>
                      <span className={game.has_boxscore ? styles.check : styles.x}>✓</span>
                    </td>
                    <td>
                      <span className={game.has_player_stats ? styles.check : styles.x}>✓</span>
                    </td>
                    <td>
                      <span className={game.has_odds ? styles.check : styles.x}>✓</span>
                    </td>
                  </>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </>
  );
}

