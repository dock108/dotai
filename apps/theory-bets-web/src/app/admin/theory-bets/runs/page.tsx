"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";
import { AdminCard } from "@/components/admin";
import { listTheoryRuns, TheoryRunListItem } from "@/lib/api/theoryRunsAdmin";

export default function TheoryRunsAdminPage() {
  const [runs, setRuns] = useState<TheoryRunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sport, setSport] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sport, status, limit, offset]);

  async function loadRuns() {
    setLoading(true);
    setError(null);
    try {
      const data = await listTheoryRuns({ sport: sport || undefined, status: status || undefined, limit, offset });
      setRuns(data.runs || []);
      setTotal(data.total || 0);
      if (data.next_offset === null && offset > 0 && (runs.length === 0 || offset >= total)) {
        setOffset(0);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const showingEnd = Math.min(offset + limit, total || offset + runs.length);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Theory Runs</h1>
        <p className={styles.subtitle}>Trace v1 pipeline runs with full results</p>
      </header>

      <div className={styles.filtersCard}>
        <div className={styles.filterRow}>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Sport</label>
            <select
              className={styles.input}
              value={sport}
              onChange={(e) => {
                setSport(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">All</option>
              <option value="NBA">NBA</option>
              <option value="NFL">NFL</option>
              <option value="MLB">MLB</option>
              <option value="NHL">NHL</option>
              <option value="NCAAB">NCAAB</option>
              <option value="NCAAF">NCAAF</option>
            </select>
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Status</label>
            <select
              className={styles.input}
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Page size</label>
            <select
              className={styles.input}
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setOffset(0);
              }}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      </div>

      {error && <div className={styles.error}>Error: {error}</div>}
      {loading && <div className={styles.loading}>Loading runs...</div>}

      {!loading && !error && runs.length === 0 && <div className={styles.empty}>No theory runs found</div>}

      {!loading && !error && runs.length > 0 && (
        <div className={styles.runList}>
          {runs.map((run) => (
            <AdminCard key={run.id} title={`Run #${run.id}`}>
              <div className={styles.runContent}>
                <div className={styles.row}>
                  <span className={styles.label}>Sport</span>
                  <span>{run.sport}</span>
                </div>
                <div className={styles.row}>
                  <span className={styles.label}>Status</span>
                  <span className={`${styles.badge} ${styles[`status_${run.status}`] || ""}`}>{run.status}</span>
                </div>
                <div className={styles.row}>
                  <span className={styles.label}>Created</span>
                  <span>{new Date(run.created_at).toLocaleString()}</span>
                </div>
                {run.completed_at && (
                  <div className={styles.row}>
                    <span className={styles.label}>Completed</span>
                    <span>{new Date(run.completed_at).toLocaleString()}</span>
                  </div>
                )}
                <div className={styles.textBlock}>
                  <p>{run.theory_text}</p>
                </div>
                <div className={styles.actions}>
                  <Link href={`/theory/${run.id}`} target="_blank" className={styles.linkButton}>
                    View Results
                  </Link>
                </div>
              </div>
            </AdminCard>
          ))}
        </div>
      )}

      {runs.length > 0 && (
        <div className={styles.pagination}>
          <button
            className={styles.paginationButton}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            ← Previous
          </button>
          <span className={styles.pageInfo}>
            Showing {offset + 1}–{showingEnd} of {total || runs.length + offset}
          </span>
          <button
            className={styles.paginationButton}
            onClick={() => setOffset(offset + limit)}
            disabled={runs.length < limit}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

