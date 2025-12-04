"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import styles from "./page.module.css";
import { AdminCard } from "@/components/admin";

interface TheoryRequest {
  id: number;
  domain: string;
  raw_text: string;
  normalized_text: string | null;
  created_at: string;
  user_id: number | null;
  evaluation?: {
    id: number;
    verdict: string;
    confidence: number;
    reasoning: string;
    created_at: string;
  };
}

/**
 * Admin page for viewing theory evaluation requests.
 * Shows original requests, derived/processed versions, and evaluation results.
 */
export default function TheoryRequestsPage() {
  const [requests, setRequests] = useState<TheoryRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [domainFilter, setDomainFilter] = useState<string>("bets");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    loadRequests();
  }, [domainFilter, limit, offset]);

  async function loadRequests() {
    setLoading(true);
    setError(null);
    try {
      const apiBase = process.env.NEXT_PUBLIC_THEORY_ENGINE_URL || "http://localhost:8000";
      const url = new URL(`${apiBase}/api/admin/theories`);
      url.searchParams.set("domain", domainFilter);
      url.searchParams.set("limit", limit.toString());
      url.searchParams.set("offset", offset.toString());
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`Failed to load requests: ${response.statusText}`);
      }
      const data = await response.json();
      setRequests(data.requests || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Theory Requests</h1>
        <p className={styles.subtitle}>Trace user theory evaluations and their derived processing</p>
      </header>

      <div className={styles.filtersCard}>
        <div className={styles.filterRow}>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Domain</label>
            <select
              className={styles.input}
              value={domainFilter}
              onChange={(e) => {
                setDomainFilter(e.target.value);
                setOffset(0);
              }}
            >
              <option value="bets">Bets</option>
              <option value="crypto">Crypto</option>
              <option value="stocks">Stocks</option>
              <option value="conspiracies">Conspiracies</option>
              <option value="playlist">Playlist</option>
            </select>
          </div>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Limit</label>
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
      {loading && <div className={styles.loading}>Loading requests...</div>}

      {!loading && !error && requests.length === 0 && (
        <div className={styles.empty}>No theory requests found</div>
      )}

      {!loading && !error && requests.length > 0 && (
        <div className={styles.requestsList}>
          {requests.map((request) => (
            <AdminCard key={request.id} title={`Request #${request.id}`}>
              <div className={styles.requestContent}>
                <div className={styles.requestSection}>
                  <h3 className={styles.sectionTitle}>Original Request</h3>
                  <div className={styles.textBlock}>
                    <p className={styles.rawText}>{request.raw_text}</p>
                  </div>
                  <div className={styles.metaRow}>
                    <span className={styles.metaItem}>
                      <strong>Domain:</strong> {request.domain}
                    </span>
                    <span className={styles.metaItem}>
                      <strong>Created:</strong> {new Date(request.created_at).toLocaleString()}
                    </span>
                    {request.user_id && (
                      <span className={styles.metaItem}>
                        <strong>User ID:</strong> {request.user_id}
                      </span>
                    )}
                  </div>
                </div>

                {request.normalized_text && (
                  <div className={styles.requestSection}>
                    <h3 className={styles.sectionTitle}>Derived / Normalized</h3>
                    <div className={styles.textBlock}>
                      <p className={styles.normalizedText}>{request.normalized_text}</p>
                    </div>
                  </div>
                )}

                {request.evaluation && (
                  <div className={styles.requestSection}>
                    <h3 className={styles.sectionTitle}>Evaluation Result</h3>
                    <div className={styles.evaluationCard}>
                      <div className={styles.evalHeader}>
                        <span className={styles.verdict}>{request.evaluation.verdict}</span>
                        <span className={styles.confidence}>
                          Confidence: {(request.evaluation.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className={styles.reasoning}>
                        <strong>Reasoning:</strong>
                        <p>{request.evaluation.reasoning}</p>
                      </div>
                      <div className={styles.metaRow}>
                        <span className={styles.metaItem}>
                          <strong>Evaluated:</strong> {new Date(request.evaluation.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {!request.evaluation && (
                  <div className={styles.requestSection}>
                    <div className={styles.noEvaluation}>No evaluation available yet</div>
                  </div>
                )}
              </div>
            </AdminCard>
          ))}
        </div>
      )}

      {requests.length > 0 && (
        <div className={styles.pagination}>
          <button
            className={styles.paginationButton}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            ← Previous
          </button>
          <span className={styles.pageInfo}>
            Showing {offset + 1}–{Math.min(offset + limit, requests.length + offset)} of {requests.length + offset}
          </span>
          <button
            className={styles.paginationButton}
            onClick={() => setOffset(offset + limit)}
            disabled={requests.length < limit}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

