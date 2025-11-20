"use client";

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
import { useStocksEvaluation, type StocksResponse } from "@dock108/js-core";
import styles from "./page.module.css";

export default function Home() {
  const { data, loading, error, evaluate } = useStocksEvaluation();
  const [submitError, setSubmitError] = useState<Error | null>(null);

  const handleSubmit = async (text: string) => {
    setSubmitError(null);
    try {
      await evaluate({
        text,
        domain: "stocks",
      });
    } catch (err) {
      setSubmitError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  return (
    <div className={styles.container}>
      <Container>
        <DomainHeader
          title="stocks.dock108.ai"
          subtitle="Evaluate your stock theories with fundamentals and historical analysis"
          domain="stocks"
        />

        <div className={styles.content}>
          <Section>
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
          </Section>

          {loading && (
            <Section>
              <LoadingSpinner message="Evaluating your stock theory..." />
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
              <TheoryCard response={data as StocksResponse} domain="stocks" />
            </Section>
          )}
        </div>
      </Container>
    </div>
  );
}

