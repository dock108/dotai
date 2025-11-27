import Link from "next/link";
import styles from "./styles.module.css";
import { fetchGame } from "@/lib/api/sportsAdmin";

type Params = {
  params: {
    gameId: string;
  };
};

/**
 * Legacy game detail page (deprecated in favor of /admin/boxscores/[id]).
 * 
 * This page provides a simpler view of game details with basic boxscore
 * and odds tables. The newer /admin/boxscores/[id] page offers a more
 * comprehensive tabbed interface with derived metrics, raw payloads,
 * and action buttons for rescraping.
 * 
 * Consider redirecting this route to /admin/boxscores/[gameId].
 */
export default async function GameDetailPage({ params }: Params) {
  const gameId = Number(params.gameId);
  const detail = await fetchGame(gameId);
  const game = detail.game;

  return (
    <div className={styles.container}>
      <Link href="/admin/games" className={styles.backLink}>
        ← Back to games
      </Link>

      <section className={styles.card}>
        <h1>
          {game.away_team} @ {game.home_team}
        </h1>
        <p className={styles.meta}>
          {game.league_code} &middot; {new Date(game.game_date).toLocaleString()} &middot; Status: {game.status}
        </p>

        <div className={styles.scoreLine}>
          <div>
            <span>{game.away_team}</span>
            <strong>{game.away_score ?? "—"}</strong>
          </div>
          <div>
            <span>{game.home_team}</span>
            <strong>{game.home_score ?? "—"}</strong>
          </div>
        </div>
      </section>

      <section className={styles.card}>
        <h2>Team Boxscores</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Team</th>
              <th>Role</th>
              <th>PTS</th>
              <th>REB</th>
              <th>AST</th>
              <th>TOV</th>
            </tr>
          </thead>
          <tbody>
            {detail.team_stats.map((row: any, idx: number) => (
              <tr key={`${row.team}-${idx}`}>
                <td>{row.team}</td>
                <td>{row.is_home ? "Home" : "Away"}</td>
                <td>{row.stats.points ?? "—"}</td>
                <td>{row.stats.rebounds ?? "—"}</td>
                <td>{row.stats.assists ?? "—"}</td>
                <td>{row.stats.turnovers ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className={styles.card}>
        <h2>Odds (closing)</h2>
        {detail.odds.length === 0 ? (
          <p className={styles.meta}>No odds stored for this matchup.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Book</th>
                <th>Market</th>
                <th>Side</th>
                <th>Line</th>
                <th>Price</th>
                <th>Observed at</th>
              </tr>
            </thead>
            <tbody>
              {detail.odds.map((row: any, idx: number) => (
                <tr key={`${row.book}-${idx}`}>
                  <td>{row.book}</td>
                  <td>{row.market_type}</td>
                  <td>{row.side ?? "—"}</td>
                  <td>{row.line ?? "—"}</td>
                  <td>{row.price ?? "—"}</td>
                  <td>{row.observed_at ? new Date(row.observed_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

