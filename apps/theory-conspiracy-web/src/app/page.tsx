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
import { useConspiraciesEvaluation, type ConspiraciesResponse } from "@dock108/js-core";
import styles from "./page.module.css";

export default function Home() {
  const { data, loading, error, evaluate } = useConspiraciesEvaluation();
  const [submitError, setSubmitError] = useState<Error | null>(null);

  const handleSubmit = async (text: string) => {
    setSubmitError(null);
    try {
      await evaluate({
        text,
        domain: "conspiracies",
      });
    } catch (err) {
      setSubmitError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  return (
    <div className={styles.container}>
      <Container>
        <DomainHeader
          title="conspiracies.dock108.ai"
          subtitle="Narrative-driven analysis with evidence comparison and rubric-based confidence scoring"
          domain="conspiracies"
        />

        <div className={styles.content}>
          <Section>
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
          </Section>

          {loading && (
            <Section>
              <LoadingSpinner message="Evaluating your theory..." />
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
              <TheoryCard response={data as ConspiraciesResponse} domain="conspiracies" />
            </Section>
          )}
        </div>
      </Container>
    </div>
  );
}

