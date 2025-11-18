"use client";

import { useState } from "react";
import { TheoryForm, TheoryCard, type TheoryResponse } from "@dock108/ui-kit";
import styles from "./page.module.css";

const THEORY_ENGINE_URL = process.env.NEXT_PUBLIC_THEORY_ENGINE_URL || "http://localhost:8000";

export default function Home() {
  const [response, setResponse] = useState<TheoryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (text: string) => {
    setLoading(true);
    setResponse(null);

    try {
      const res = await fetch(`${THEORY_ENGINE_URL}/api/theory/stocks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          domain: "stocks",
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

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>stocks.dock108.ai</h1>
        <p className={styles.subtitle}>Evaluate your stock theories with fundamentals and historical analysis</p>
      </header>

      <div className={styles.content}>
        <div className={styles.formSection}>
          <TheoryForm
            domain="stocks"
            placeholder="e.g., 'AAPL will outperform because their services revenue is growing faster than hardware'"
            examples={[
              "Tech stocks with high R&D spend outperform during innovation cycles",
              "Consumer staples with pricing power maintain margins in inflation",
              "Energy stocks correlate with oil prices but lag by 2-3 months",
            ]}
            onSubmit={handleSubmit}
            loading={loading}
          />
        </div>

        {response && (
          <div className={styles.resultSection}>
            <TheoryCard response={response} domain="stocks" />
          </div>
        )}
      </div>
    </div>
  );
}

