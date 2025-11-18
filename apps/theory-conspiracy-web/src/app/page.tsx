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
      const res = await fetch(`${THEORY_ENGINE_URL}/api/theory/conspiracies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          domain: "conspiracies",
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
        <h1>conspiracies.dock108.ai</h1>
        <p className={styles.subtitle}>Evaluate conspiracy theories with fact-checking and evidence analysis</p>
      </header>

      <div className={styles.content}>
        <div className={styles.formSection}>
          <TheoryForm
            domain="conspiracies"
            placeholder="e.g., 'JFK second shooter' or 'moon landing hoax' (not within last 90 days)"
            examples={[
              "JFK second shooter theory",
              "Moon landing hoax claims",
              "False flag claim about X (not within last 90 days)",
            ]}
            onSubmit={handleSubmit}
            loading={loading}
          />
        </div>

        {response && (
          <div className={styles.resultSection}>
            <TheoryCard response={response} domain="conspiracies" />
          </div>
        )}
      </div>
    </div>
  );
}

