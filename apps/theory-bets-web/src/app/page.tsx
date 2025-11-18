"use client";

import { useState } from "react";
import { TheoryForm, TheoryCard, type TheoryResponse } from "@dock108/ui-kit";
import styles from "./page.module.css";

const THEORY_ENGINE_URL = process.env.NEXT_PUBLIC_THEORY_ENGINE_URL || "http://localhost:8000";

export default function Home() {
  const [response, setResponse] = useState<TheoryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (text: string, extraFields?: Record<string, any>) => {
    setLoading(true);
    setResponse(null);

    try {
      const res = await fetch(`${THEORY_ENGINE_URL}/api/theory/bets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          domain: "bets",
          sport: extraFields?.sport,
          league: extraFields?.league,
          horizon: extraFields?.horizon || "single_game",
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to evaluate theory");
      }

      const data = await res.json();
      setResponse(data);
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const extraFields = (
    <div className={styles.extraFields}>
      <label className={styles.fieldLabel}>
        Sport
        <input
          type="text"
          className={styles.fieldInput}
          placeholder="MLB, NBA, NFL, etc."
          name="sport"
        />
      </label>
      <label className={styles.fieldLabel}>
        League
        <input
          type="text"
          className={styles.fieldInput}
          placeholder="Optional league name"
          name="league"
        />
      </label>
      <label className={styles.fieldLabel}>
        Horizon
        <select className={styles.fieldInput} name="horizon" defaultValue="single_game">
          <option value="single_game">Single Game</option>
          <option value="full_season">Full Season</option>
        </select>
      </label>
    </div>
  );

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>bets.dock108.ai</h1>
        <p className={styles.subtitle}>Evaluate your betting theories with data-driven analysis</p>
      </header>

      <div className={styles.content}>
        <div className={styles.formSection}>
          <TheoryForm
            domain="bets"
            placeholder="e.g., 'The Lakers will cover the spread because their defense improved after the trade deadline'"
            examples={[
              "MLB moneyline trend: Teams with 3+ consecutive wins have 65% win rate",
              "NCAAB spreads: Home favorites in conference games cover 58% of the time",
              "NFL totals: Games in domes average 5 points higher than outdoor games",
            ]}
            onSubmit={handleSubmit}
            extraFields={extraFields}
            loading={loading}
          />
        </div>

        {response && (
          <div className={styles.resultSection}>
            <TheoryCard response={response} domain="bets" />
          </div>
        )}
      </div>
    </div>
  );
}

