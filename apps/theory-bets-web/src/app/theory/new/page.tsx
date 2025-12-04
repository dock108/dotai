"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";
import { createTheoryRun } from "@/lib/api/theoryRuns";
import { TheoryRunRequest } from "@/lib/types/theoryRuns";

const SPORTS = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF"];

export default function BuildTheoryPage() {
  const router = useRouter();
  const [sport, setSport] = useState("NBA");
  const [theory, setTheory] = useState("");
  const [userStats, setUserStats] = useState("");
  const [userBetTypes, setUserBetTypes] = useState("spread");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload: TheoryRunRequest = {
        sport,
        theory_text: theory,
        user_stats: userStats ? userStats.split(",").map((s) => s.trim()) : undefined,
        user_bet_types: userBetTypes ? userBetTypes.split(",").map((s) => s.trim()) : undefined,
      };
      const result = await createTheoryRun(payload);
      setSuggestions(result.prompt_feedback || []);
      router.push(`/theory/${result.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Build a Theory</h1>
        <p className={styles.subtitle}>Run the v1 pipeline with last-seen odds</p>
      </header>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Sport</label>
          <select className={styles.input} value={sport} onChange={(e) => setSport(e.target.value)}>
            {SPORTS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Theory</label>
          <textarea
            className={styles.textarea}
            value={theory}
            onChange={(e) => setTheory(e.target.value)}
            placeholder="e.g., Altitude back-to-backs favor home spreads"
            required
            rows={6}
          />
        </div>

        <details className={styles.advanced}>
          <summary>Advanced options</summary>
          <div className={styles.advancedBody}>
            <label className={styles.label}>Stats override (comma-separated)</label>
            <input
              className={styles.input}
              value={userStats}
              onChange={(e) => setUserStats(e.target.value)}
              placeholder="pace, altitude, back_to_back"
            />
            <label className={styles.label}>Bet types override (comma-separated)</label>
            <input
              className={styles.input}
              value={userBetTypes}
              onChange={(e) => setUserBetTypes(e.target.value)}
              placeholder="spread,total,moneyline"
            />
          </div>
        </details>

        <button className={styles.submit} type="submit" disabled={loading}>
          {loading ? "Running..." : "Run Theory"}
        </button>
      </form>

      {error && <div className={styles.error}>{error}</div>}

      {suggestions.length > 0 && (
        <div className={styles.suggestions}>
          <h3>Prompt suggestions</h3>
          <ul>
            {suggestions.map((s, idx) => (
              <li key={idx}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

