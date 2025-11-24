"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import styles from "./styles.module.css";
import { listGames, type GameSummary, type GameFilters } from "@/lib/api/sportsAdmin";

const LEAGUES = ["NBA", "NCAAB", "NFL", "NCAAF", "MLB", "NHL"];

/**
 * Legacy games browser page (deprecated in favor of /admin/boxscores).
 * 
 * This page provides a simpler interface for browsing games by league and season.
 * The newer /admin/boxscores page offers more comprehensive filtering, pagination,
 * and completeness indicators. Consider redirecting this route to /admin/boxscores.
 */
export default function GamesAdminPage() {
  const [league, setLeague] = useState("NBA");
  const [season, setSeason] = useState("");
  const [games, setGames] = useState<GameSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGames = async () => {
    try {
      setLoading(true);
      // Convert to new API format
      const filters: GameFilters = {
        leagues: [league],
        season: season ? Number(season) : undefined,
        limit: 100,
        offset: 0,
      };
      const response = await listGames(filters);
      setGames(response.games);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGames();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [league]);

  return (
    <div className={styles.container}>
      <h1>Games Browser</h1>
      <p className={styles.subtitle}>Inspect ingested games, boxscores, and odds.</p>

      <section className={styles.filters}>
        <label>
          League
          <select value={league} onChange={(e) => setLeague(e.target.value)}>
            {LEAGUES.map((code) => (
              <option key={code}>{code}</option>
            ))}
          </select>
        </label>

        <label>
          Season
          <input type="number" value={season} onChange={(e) => setSeason(e.target.value)} placeholder="2024" />
        </label>

        <button onClick={fetchGames} disabled={loading}>
          {loading ? "Loading..." : "Apply"}
        </button>
      </section>

      {error && <p className={styles.error}>{error}</p>}

      <section className={styles.card}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Matchup</th>
              <th>Score</th>
              <th>Boxscore</th>
              <th>Odds</th>
            </tr>
          </thead>
          <tbody>
            {games.map((game) => (
              <tr key={game.id}>
                <td>{new Date(game.game_date).toLocaleDateString()}</td>
                <td>
                  <Link href={`/admin/theory-bets/games/${game.id}`}>
                    {game.away_team} @ {game.home_team}
                  </Link>
                </td>
                <td>
                  {game.away_score ?? "—"} - {game.home_score ?? "—"}
                </td>
                <td>{game.has_boxscore ? "✅" : "—"}</td>
                <td>{game.has_odds ? "✅" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

