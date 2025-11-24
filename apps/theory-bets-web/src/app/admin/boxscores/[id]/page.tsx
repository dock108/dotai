"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";
import { ErrorDisplay, LoadingSpinner } from "@dock108/ui-kit";
import { AdminGameDetail, fetchGame, rescrapeGame, resyncOdds } from "@/lib/api/sportsAdmin";

/**
 * Available tabs for the game detail view.
 */
const TABS = ["summary", "team", "players", "odds", "metrics", "raw", "actions"] as const;

type TabKey = (typeof TABS)[number];

/**
 * Game detail page wrapper component.
 * 
 * Extracts game ID from route params and renders the client component.
 */
export default function GameDetailPage({ params }: { params: { id: string } }) {
  const gameId = Number(params.id);
  return <GameDetailClient gameId={gameId} />;
}

/**
 * Game detail client component with tabbed interface.
 * 
 * Displays comprehensive game information including:
 * - Summary: Basic game metadata and completeness flags
 * - Team: Team-level boxscore statistics
 * - Players: Individual player statistics with search
 * - Odds: Betting lines from various books
 * - Metrics: Derived metrics (spread results, totals, efficiency)
 * - Raw: Raw scraped payloads for debugging
 * - Actions: Buttons to trigger rescrape or odds resync
 * 
 * Supports rescraping boxscores and resyncing odds via Celery tasks.
 */
function GameDetailClient({ gameId }: { gameId: number }) {
  const [detail, setDetail] = useState<AdminGameDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("summary");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [playerSearch, setPlayerSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchGame(gameId);
        if (!cancelled) setDetail(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load game");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [gameId]);

  const filteredPlayers = useMemo(() => {
    if (!detail) return [];
    if (!playerSearch.trim()) return detail.player_stats;
    const needle = playerSearch.toLowerCase();
    return detail.player_stats.filter(
      (player) =>
        player.player_name.toLowerCase().includes(needle) ||
        player.team.toLowerCase().includes(needle),
    );
  }, [detail, playerSearch]);

  const handleAction = async (type: "rescrape" | "resync") => {
    try {
      setActionBusy(true);
      if (type === "rescrape") {
        await rescrapeGame(gameId);
        setActionMessage("Rescrape triggered — refresh in ~30 seconds.");
      } else {
        await resyncOdds(gameId);
        setActionMessage("Odds resync queued — refresh soon.");
      }
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionBusy(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.centered}>
        <LoadingSpinner message="Loading game detail..." />
      </div>
    );
  }

  if (error || !detail) {
    return <ErrorDisplay error={new Error(error ?? "Missing game")} title="Unable to load game detail" />;
  }

  const { game } = detail;
  const formattedDate = new Date(game.game_date).toLocaleString();

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <Link href="/admin/boxscores" className={styles.backLink}>
            ← Back to games
          </Link>
          <p className={styles.eyebrow}>{game.league_code} • {game.season}</p>
          <h1>
            {detail.game.away_team} @ {detail.game.home_team}
          </h1>
          <p className={styles.subtitle}>
            {formattedDate} • Status: {game.status} • Version {game.scrape_version ?? "-"}
          </p>
        </div>
        <div className={styles.scoreCard}>
          <div>
            <span>{detail.game.away_team}</span>
            <strong>{detail.game.away_score ?? "-"}</strong>
          </div>
          <div>
            <span>{detail.game.home_team}</span>
            <strong>{detail.game.home_score ?? "-"}</strong>
          </div>
        </div>
      </div>

      <div className={styles.tabRow}>
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            className={`${styles.tabButton} ${activeTab === tab ? styles.tabActive : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {activeTab === "summary" && (
        <section className={styles.card}>
          <div className={styles.summaryGrid}>
            <div>
              <label>League</label>
              <p>{game.league_code}</p>
            </div>
            <div>
              <label>Season type</label>
              <p>{game.season_type ?? "—"}</p>
            </div>
            <div>
              <label>Has boxscore</label>
              <p>{game.has_boxscore ? "Yes" : "No"}</p>
            </div>
            <div>
              <label>Has player stats</label>
              <p>{game.has_player_stats ? "Yes" : "No"}</p>
            </div>
            <div>
              <label>Has odds</label>
              <p>{game.has_odds ? "Yes" : "No"}</p>
            </div>
            <div>
              <label>Last scraped</label>
              <p>{game.last_scraped_at ? new Date(game.last_scraped_at).toLocaleString() : "—"}</p>
            </div>
          </div>
        </section>
      )}

      {activeTab === "team" && (
        <section className={styles.card}>
          <h2>Team Stats</h2>
          <div className={styles.statGrid}>
            {detail.team_stats.map((stat) => (
              <div key={`${stat.team}-${stat.is_home}`} className={styles.statCard}>
                <div className={styles.statHeader}>
                  <strong>{stat.team}</strong>
                  <span>{stat.is_home ? "Home" : "Away"}</span>
                </div>
                <ul>
                  {Object.entries(stat.stats).map(([key, value]) => (
                    <li key={key}>
                      <span>{key}</span>
                      <span>{String(value)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {activeTab === "players" && (
        <section className={styles.card}>
          <div className={styles.playersHeader}>
            <h2>Player Stats</h2>
            <input
              type="text"
              placeholder="Search player or team"
              value={playerSearch}
              onChange={(e) => setPlayerSearch(e.target.value)}
            />
          </div>
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Team</th>
                  <th>Player</th>
                  <th>Minutes</th>
                  <th>Points</th>
                  <th>Reb</th>
                  <th>Ast</th>
                  <th>Yards</th>
                  <th>TD</th>
                </tr>
              </thead>
              <tbody>
                {filteredPlayers.map((player, idx) => (
                  <tr key={`${player.player_name}-${idx}`}>
                    <td>{player.team}</td>
                    <td>
                      <details>
                        <summary>{player.player_name}</summary>
                        <pre>{JSON.stringify(player.raw_stats, null, 2)}</pre>
                      </details>
                    </td>
                    <td>{player.minutes ?? "—"}</td>
                    <td>{player.points ?? "—"}</td>
                    <td>{player.rebounds ?? "—"}</td>
                    <td>{player.assists ?? "—"}</td>
                    <td>{player.yards ?? "—"}</td>
                    <td>{player.touchdowns ?? "—"}</td>
                  </tr>
                ))}
                {!filteredPlayers.length && (
                  <tr>
                    <td colSpan={8} className={styles.emptyState}>
                      No players match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === "odds" && (
        <section className={styles.card}>
          <h2>Closing Lines</h2>
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Book</th>
                  <th>Market</th>
                  <th>Side</th>
                  <th>Line</th>
                  <th>Price</th>
                  <th>Observed</th>
                </tr>
              </thead>
              <tbody>
                {detail.odds.map((odd, idx) => (
                  <tr key={`${odd.book}-${idx}`}>
                    <td>{odd.book}</td>
                    <td>{odd.market_type}</td>
                    <td>{odd.side ?? "—"}</td>
                    <td>{odd.line ?? "—"}</td>
                    <td>{odd.price ?? "—"}</td>
                    <td>{odd.observed_at ? new Date(odd.observed_at).toLocaleString() : "—"}</td>
                  </tr>
                ))}
                {!detail.odds.length && (
                  <tr>
                    <td colSpan={6} className={styles.emptyState}>
                      No odds available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === "metrics" && (
        <section className={styles.card}>
          <h2>Derived Metrics</h2>
          <div className={styles.metricsGrid}>
            {Object.entries(detail.derived_metrics).map(([key, value]) => (
              <div key={key} className={styles.metric}>
                <span>{key}</span>
                <strong>{typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}</strong>
              </div>
            ))}
            {!Object.keys(detail.derived_metrics).length && <p>No derived metrics yet.</p>}
          </div>
        </section>
      )}

      {activeTab === "raw" && (
        <section className={styles.card}>
          <h2>Raw Payloads</h2>
          <details open className={styles.rawBlock}>
            <summary>Team boxscores</summary>
            <pre>{JSON.stringify(detail.raw_payloads.team_boxscores, null, 2)}</pre>
          </details>
          <details className={styles.rawBlock}>
            <summary>Player boxscores</summary>
            <pre>{JSON.stringify(detail.raw_payloads.player_boxscores, null, 2)}</pre>
          </details>
          <details className={styles.rawBlock}>
            <summary>Odds payloads</summary>
            <pre>{JSON.stringify(detail.raw_payloads.odds, null, 2)}</pre>
          </details>
        </section>
      )}

      {activeTab === "actions" && (
        <section className={styles.card}>
          <h2>Actions</h2>
          <div className={styles.actionButtons}>
            <button type="button" disabled={actionBusy} onClick={() => handleAction("rescrape")}>
              Re-scrape boxscore
            </button>
            <button type="button" disabled={actionBusy} onClick={() => handleAction("resync")}>
              Re-sync odds
            </button>
            <a
              href={`https://www.sports-reference.com/search/search.fcgi?search=${encodeURIComponent(
                `${detail.game.away_team} ${detail.game.home_team}`,
              )}`}
              target="_blank"
              rel="noreferrer"
            >
              Open in sports-reference ↗
            </a>
            <a
              download={`game-${gameId}.json`}
              href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(detail, null, 2))}`}
            >
              Export JSON
            </a>
          </div>
          {actionMessage && <p className={styles.actionMessage}>{actionMessage}</p>}
        </section>
      )}
    </div>
  );
}

