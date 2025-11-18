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
      const res = await fetch(`${THEORY_ENGINE_URL}/api/theory/crypto`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          domain: "crypto",
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
        <h1>crypto.dock108.ai</h1>
        <p className={styles.subtitle}>Evaluate your crypto theories with historical pattern analysis</p>
      </header>

      <div className={styles.content}>
        <div className={styles.formSection}>
          <TheoryForm
            domain="crypto"
            placeholder="e.g., 'I think bitcoin will go down because altcoin liquidity is going up'"
            examples={[
              "Bitcoin dominance dropping means alt season is coming",
              "ETH/BTC ratio breaking out signals rotation into alts",
              "Stablecoin supply increasing predicts bull market continuation",
            ]}
            onSubmit={handleSubmit}
            loading={loading}
          />
        </div>

        {response && (
          <div className={styles.resultSection}>
            <TheoryCard response={response} domain="crypto" />
          </div>
        )}
      </div>
    </div>
  );
}

