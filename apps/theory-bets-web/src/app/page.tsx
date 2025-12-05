"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { TheoryForm, DomainHeader, ErrorDisplay, LoadingSpinner, Container, Section } from "@dock108/ui-kit";
import { createTheoryRun } from "@/lib/api/theoryRuns";
import { TheoryRunRequest } from "@/lib/types/theoryRuns";
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
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handleSubmit = async (text: string, extraFields?: Record<string, any>) => {
    setError(null);
    setLoading(true);
    try {
      const payload: TheoryRunRequest = {
        sport: (extraFields?.sport as string) || "NBA",
        theory_text: text,
        user_stats: extraFields?.user_stats
          ? String(extraFields.user_stats)
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : undefined,
        user_bet_types: extraFields?.user_bet_types
          ? String(extraFields.user_bet_types)
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : undefined,
      };
      const result = await createTheoryRun(payload);
      if (result.run_id) {
        router.push(`/theory/${result.run_id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  };

  const extraFields = (
    <div className={styles.extraFields}>
      <label className={styles.fieldLabel}>
        Sport
        <select className={styles.fieldInput} name="sport" defaultValue="NBA">
          <option value="NBA">NBA</option>
          <option value="NFL">NFL</option>
          <option value="MLB">MLB</option>
          <option value="NHL">NHL</option>
          <option value="NCAAB">NCAAB</option>
          <option value="NCAAF">NCAAF</option>
        </select>
      </label>
      <label className={styles.fieldLabel}>
        Stats override (comma-separated)
        <input type="text" className={styles.fieldInput} placeholder="pace, altitude, back_to_back" name="user_stats" />
      </label>
      <label className={styles.fieldLabel}>
        Bet types override (comma-separated)
        <input type="text" className={styles.fieldInput} placeholder="spread,total,moneyline" name="user_bet_types" />
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
              <LoadingSpinner message="Running theory v1 pipeline..." />
            </Section>
          )}

          {error && (
            <Section>
              <ErrorDisplay
                error={error || new Error("Unknown error")}
                title="Failed to Evaluate Theory"
                onRetry={() => {
                  setError(null);
                }}
              />
          </Section>
        )}
      </div>

      <nav className={styles.navLinks}>
        <Link href="/admin/theory-bets/runs" className={styles.adminLink}>
          Admin: Trace Runs
        </Link>
        <Link href="/admin/theory-bets/browser" className={styles.adminLink}>
          Admin: Data Browser
      </Link>
      </nav>
      </Container>
    </div>
  );
}

