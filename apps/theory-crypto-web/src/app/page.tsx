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
import { useCryptoEvaluation, type CryptoResponse } from "@dock108/js-core";
import styles from "./page.module.css";

export default function Home() {
  const { data, loading, error, evaluate } = useCryptoEvaluation();
  const [submitError, setSubmitError] = useState<Error | null>(null);

  const handleSubmit = async (text: string) => {
    setSubmitError(null);
    try {
      await evaluate({
        text,
        domain: "crypto",
      });
    } catch (err) {
      setSubmitError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  return (
    <div className={styles.container}>
      <Container>
        <DomainHeader
          title="crypto.dock108.ai"
          subtitle="Evaluate your crypto theories with historical pattern analysis"
          domain="crypto"
        />

        <div className={styles.content}>
          <Section>
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
          </Section>

          {loading && (
            <Section>
              <LoadingSpinner message="Evaluating your crypto theory..." />
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
              <TheoryCard response={data as CryptoResponse} domain="crypto" />
            </Section>
          )}
        </div>
      </Container>
    </div>
  );
}

