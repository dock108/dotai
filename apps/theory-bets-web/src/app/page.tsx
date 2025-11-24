"use client";

import Link from "next/link";
import { useState } from "react";
import {
  TheoryForm,
  TheoryCard,
  DomainHeader,
  ErrorDisplay,
  LoadingSpinner,
  Container,
  Section,
} from "@dock108/ui-kit";
import { useBetsEvaluation, type BetsRequest, type BetsResponse } from "@dock108/js-core";
import styles from "./page.module.css";

/**
 * Main page component for betting theory evaluation.
 * 
 * Provides a query builder interface where users can:
 * - Enter a betting theory (e.g., "Lakers will cover the spread")
 * - Specify sport, league, and time horizon (single game vs full season)
 * - Receive AI-powered analysis with data-driven feedback
 * 
 * Uses the shared useBetsEvaluation hook from @dock108/js-core
 * which handles API communication with the theory-engine-api backend.
 */
export default function Home() {
  const { data, loading, error, evaluate } = useBetsEvaluation();
  const [submitError, setSubmitError] = useState<Error | null>(null);

  const handleSubmit = async (text: string, extraFields?: Record<string, any>) => {
    setSubmitError(null);
    try {
      const request: BetsRequest = {
        text,
        domain: "bets",
        sport: extraFields?.sport || null,
        league: extraFields?.league || null,
        horizon: extraFields?.horizon || "single_game",
      };
      await evaluate(request);
    } catch (err) {
      setSubmitError(err instanceof Error ? err : new Error(String(err)));
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
      <Container>
        <DomainHeader
          title="bets.dock108.ai"
          subtitle="Evaluate your betting theories with data-driven analysis"
          domain="bets"
        />

        <div className={styles.content}>
          <Section>
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
          </Section>

          {loading && (
            <Section>
              <LoadingSpinner message="Evaluating your betting theory..." />
            </Section>
          )}

          {(error || submitError) && (
            <Section>
              <ErrorDisplay
                error={error || submitError || new Error("Unknown error")}
                title="Failed to Evaluate Theory"
                onRetry={() => {
                  setSubmitError(null);
                  // Retry is handled by the form resubmission
                }}
              />
            </Section>
          )}

          {data && (
            <Section>
              <TheoryCard response={data as BetsResponse} domain="bets" />
            </Section>
          )}
        </div>

        <Link href="/admin/theory-bets/ingestion" className={styles.adminLink}>
          Open sports data admin →
        </Link>
      </Container>
    </div>
  );
}

