"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";
import {
  listStocksIngestionRuns,
  listEquityAssets,
  listEquityCandles,
  type StocksIngestionRunResponse,
} from "@/lib/api/stocksAdmin";
import { getStatusClass } from "@/lib/utils/status";

interface StocksDashboardStats {
  totalAssets: number;
  totalCandles: number;
  totalRuns: number;
  pendingRuns: number;
  runningRuns: number;
}

export default function StocksAdminDashboardPage() {
  const [stats, setStats] = useState<StocksDashboardStats | null>(null);
  const [recentRuns, setRecentRuns] = useState<StocksIngestionRunResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);

        const [runs, assetsResponse, candlesResponse] = await Promise.all([
          listStocksIngestionRuns({ limit: 50 }),
          listEquityAssets({ limit: 1, offset: 0 }),
          listEquityCandles({ limit: 1, offset: 0 }),
        ]);

        const pending = runs.filter((r) => r.status === "pending").length;
        const running = runs.filter((r) => r.status === "running").length;

        setStats({
          totalAssets: assetsResponse.total,
          totalCandles: candlesResponse.total,
          totalRuns: runs.length,
          pendingRuns: pending,
          runningRuns: running,
        });

        setRecentRuns(runs.slice(0, 5));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const getStatusClassName = (status: string) => {
    const baseClass = getStatusClass(status);
    return styles[baseClass] || styles.runStatus;
  };

  if (loading) {
    return <div className={styles.loading}>Loading stocks dashboard...</div>;
  }

  if (error) {
    return <div className={styles.error}>Error: {error}</div>;
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Stocks Admin</h1>
        <p className={styles.subtitle}>Equities ingestion overview and quick actions</p>
      </header>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Tracked Assets</div>
          <div className={styles.statValue}>{stats?.totalAssets.toLocaleString() ?? 0}</div>
          <div className={styles.statSub}>Across all exchanges</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Candles</div>
          <div className={styles.statValue}>{stats?.totalCandles.toLocaleString() ?? 0}</div>
          <div className={styles.statSub}>Total OHLCV rows</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Ingestion Runs</div>
          <div className={styles.statValue}>{stats?.totalRuns ?? 0}</div>
          <div className={styles.statSub}>Total completed</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Pending</div>
          <div className={styles.statValue}>{stats?.pendingRuns ?? 0}</div>
          <div className={styles.statSub}>Jobs in queue</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Running</div>
          <div className={styles.statValue}>{stats?.runningRuns ?? 0}</div>
          <div className={styles.statSub}>Active workers</div>
        </div>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Quick Actions</h2>
        <div className={styles.quickLinks}>
          <Link href="/admin/theory-stocks/ingestion" className={styles.quickLink}>
            <div className={styles.quickLinkIcon}>⚙️</div>
            <div className={styles.quickLinkContent}>
              <div className={styles.quickLinkTitle}>New Ingestion Run</div>
              <div className={styles.quickLinkDesc}>Schedule a new stocks ingestion job</div>
            </div>
            <div className={styles.quickLinkArrow}>→</div>
          </Link>
          <Link href="/admin/theory-stocks/assets" className={styles.quickLink}>
            <div className={styles.quickLinkIcon}>🏛️</div>
            <div className={styles.quickLinkContent}>
              <div className={styles.quickLinkTitle}>Browse Assets</div>
              <div className={styles.quickLinkDesc}>View tracked exchanges and tickers</div>
            </div>
            <div className={styles.quickLinkArrow}>→</div>
          </Link>
        </div>
      </section>

      {recentRuns.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Recent Runs</h2>
          <div className={styles.recentRuns}>
            {recentRuns.map((run) => (
              <Link
                key={run.id}
                href={`/admin/theory-stocks/ingestion/${run.id}`}
                className={styles.runItem}
              >
                <div className={`${styles.runStatus} ${getStatusClassName(run.status)}`} />
                <div className={styles.runInfo}>
                  <div className={styles.runTitle}>
                    {run.exchange_code} — {run.timeframe} — {run.status}
                  </div>
                  <div className={styles.runMeta}>
                    {run.start_time || "?"} → {run.end_time || "?"}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}


