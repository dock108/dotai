"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchGame, rescrapeGame, resyncOdds, type AdminGameDetail } from "@/lib/api/sportsAdmin";
import styles from "./styles.module.css";

export default function GameDetailClient() {
  const params = useParams<{ gameId?: string }>();
  const gameIdParam = params?.gameId ?? "";
  const isNumericId = /^\d+$/.test(gameIdParam);
  const [game, setGame] = useState<AdminGameDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<"rescrape" | "odds" | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGame(gameIdParam);
      setGame(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load game");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isNumericId) {
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNumericId, gameIdParam]);

  const flags = useMemo(() => {
    if (!game) return [];
    return [
      { label: "Boxscore", ok: game.game.has_boxscore },
      { label: "Player stats", ok: game.game.has_player_stats },
      { label: "Odds", ok: game.game.has_odds },
    ];
  }, [game]);

  const handleRescrape = async () => {
    setActionStatus(null);
    setActionLoading("rescrape");
    try {
      const res = await rescrapeGame(Number.parseInt(gameIdParam, 10));
      setActionStatus(res.message || "Rescrape requested");
    } catch (err) {
      setActionStatus(err instanceof Error ? err.message : "Rescrape failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleResyncOdds = async () => {
    setActionStatus(null);
    setActionLoading("odds");
    try {
      const res = await resyncOdds(Number.parseInt(gameIdParam, 10));
      setActionStatus(res.message || "Odds resync requested");
    } catch (err) {
      setActionStatus(err instanceof Error ? err.message : "Odds resync failed");
    } finally {
      setActionLoading(null);
    }
  };

  if (!isNumericId) return <div className={styles.container}>Invalid game id.</div>;
  if (loading) return <div className={styles.container}>Loading game...</div>;
  if (error) return <div className={styles.container}>Error: {error}</div>;
  if (!game) return <div className={styles.container}>Game not found.</div>;

  const g = game.game;
  const gameDate = new Date(g.game_date).toLocaleString();

  return (
    <div className={styles.container}>
      <Link href="/admin/theory-bets/browser" className={styles.backLink}>
        ← Back to Data Browser
      </Link>

      <div className={styles.card}>
        <h1>
          Game {g.id} — {g.league_code}
        </h1>
        <div className={styles.meta}>
          {gameDate} · {g.season_type ?? "season"} · Last scraped: {g.last_scraped_at ?? "—"}
        </div>
        <div className={styles.scoreLine}>
          <div>
            <strong>{g.away_team}</strong>
            <span>Away</span>
            <span>{g.away_score ?? "—"}</span>
          </div>
          <div>
            <strong>{g.home_team}</strong>
            <span>Home</span>
            <span>{g.home_score ?? "—"}</span>
          </div>
        </div>
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          {flags.map((f) => (
            <span
              key={f.label}
              style={{
                padding: "0.35rem 0.75rem",
                borderRadius: "999px",
                background: f.ok ? "#ecfdf3" : "#fef2f2",
                color: f.ok ? "#166534" : "#b91c1c",
                fontWeight: 700,
                fontSize: "0.85rem",
              }}
            >
              {f.label}: {f.ok ? "Yes" : "No"}
            </span>
          ))}
        </div>
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={handleRescrape}
            disabled={!!actionLoading}
            style={{ padding: "0.55rem 0.9rem", borderRadius: 8, border: "1px solid #cbd5e1" }}
          >
            {actionLoading === "rescrape" ? "Requesting..." : "Rescrape game"}
          </button>
          <button
            type="button"
            onClick={handleResyncOdds}
            disabled={!!actionLoading}
            style={{ padding: "0.55rem 0.9rem", borderRadius: 8, border: "1px solid #cbd5e1" }}
          >
            {actionLoading === "odds" ? "Requesting..." : "Resync odds"}
          </button>
          <button
            type="button"
            onClick={load}
            disabled={!!actionLoading}
            style={{ padding: "0.55rem 0.9rem", borderRadius: 8, border: "1px solid #cbd5e1" }}
          >
            Refresh
          </button>
        </div>
        {actionStatus && <div style={{ marginTop: "0.5rem", color: "#0f172a" }}>{actionStatus}</div>}
      </div>

      <div className={styles.card}>
        <h2>Odds</h2>
        {game.odds.length === 0 ? (
          <div style={{ color: "#475569" }}>No odds found.</div>
        ) : (
          <table className={styles.table}>
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
              {game.odds.map((o, idx) => (
                <tr key={`${o.book}-${o.market_type}-${o.side}-${idx}`}>
                  <td>{o.book}</td>
                  <td>{o.market_type}</td>
                  <td>{o.side ?? "—"}</td>
                  <td>{o.line ?? "—"}</td>
                  <td>{o.price ?? "—"}</td>
                  <td>{o.observed_at ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className={styles.card}>
        <h2>Derived metrics</h2>
        {Object.keys(game.derived_metrics || {}).length === 0 ? (
          <div style={{ color: "#475569" }}>No derived metrics.</div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(game.derived_metrics).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{String(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

