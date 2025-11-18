"use client";

import styles from "./TheoryCard.module.css";

export interface DataSource {
  name: string;
  cache_status: string;
  details?: string;
}

export interface TheoryResponse {
  // 1. Summary
  summary: string;

  // 2. Verdict + Confidence
  verdict: string;
  confidence: number;

  // 3. Data we used
  data_used: DataSource[];

  // 4. How we got the conclusion
  how_we_got_conclusion: string[];

  // 5. Long-term $100 example
  long_term_outcome_example: string;

  // 6. Limits / missing data
  limitations: string[];

  // 7. Meta
  guardrail_flags: string[];
  model_version?: string;
  evaluation_date?: string;

  // Domain-specific extensions (for backward compatibility)
  likelihood_grade?: string;
  edge_estimate?: number;
  kelly_sizing_example?: string;
  pattern_frequency?: number;
  failure_periods?: string[];
  remaining_edge?: number;
  correlation_grade?: string;
  fundamentals_match?: boolean;
  volume_analysis?: string;
  likelihood_rating?: number;
  evidence_for?: string[];
  evidence_against?: string[];
  historical_parallels?: string[];
  missing_data?: string[];
}

interface TheoryCardProps {
  response: TheoryResponse;
  domain: "bets" | "crypto" | "stocks" | "conspiracies";
}

export function TheoryCard({ response, domain }: TheoryCardProps) {
  const hasHardBlock = response.guardrail_flags.some((flag) => flag.startsWith("hard:"));

  if (hasHardBlock) {
    return (
      <div className={styles.card} style={{ borderColor: "#c33" }}>
        <h3 className={styles.title} style={{ color: "#c33" }}>
          Cannot Evaluate
        </h3>
        <p className={styles.message}>
          This theory cannot be evaluated due to guardrail restrictions.
        </p>
        {response.guardrail_flags.length > 0 && (
          <div className={styles.flags}>
            <strong>Restrictions:</strong>
            <ul>
              {response.guardrail_flags.map((flag, idx) => (
                <li key={idx}>{flag}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={styles.card}>
      {/* 1. Summary */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Summary</h3>
        <p className={styles.summary}>{response.summary}</p>
      </div>

      {/* 2. Verdict + Confidence */}
      <div className={styles.section}>
        <div className={styles.verdictHeader}>
          <h3 className={styles.verdict}>{response.verdict}</h3>
          <div className={styles.confidence}>
            Confidence: {(response.confidence * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* 3. Data we used */}
      {response.data_used.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Data We Used</h3>
          <ul className={styles.dataList}>
            {response.data_used.map((source, idx) => (
              <li key={idx} className={styles.dataItem}>
                <span className={styles.dataName}>{source.name}</span>
                <span className={styles[source.cache_status === "cached" ? "cached" : "fresh"]}>
                  {source.cache_status}
                </span>
                {source.details && <span className={styles.dataDetails}>{source.details}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 4. How we got the conclusion */}
      {response.how_we_got_conclusion.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>How We Got the Conclusion</h3>
          <ul className={styles.conclusionList}>
            {response.how_we_got_conclusion.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 5. Long-term $100 example */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Long-term $100 Example</h3>
        <p className={styles.outcome}>{response.long_term_outcome_example}</p>
      </div>

      {/* 6. Limits / missing data */}
      {response.limitations.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Limits / Missing Data</h3>
          <ul className={styles.limitationsList}>
            {response.limitations.map((limitation, idx) => (
              <li key={idx}>{limitation}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 7. Meta */}
      <div className={styles.meta}>
        {response.guardrail_flags.length > 0 && (
          <div className={styles.metaItem}>
            <strong>Guardrail Flags:</strong> {response.guardrail_flags.join(", ")}
          </div>
        )}
        {response.model_version && (
          <div className={styles.metaItem}>
            <strong>Model:</strong> {response.model_version}
          </div>
        )}
        {response.evaluation_date && (
          <div className={styles.metaItem}>
            <strong>Evaluated:</strong> {new Date(response.evaluation_date).toLocaleDateString()}
          </div>
        )}
      </div>

      {/* Domain-specific extensions (for backward compatibility) */}
      {domain === "bets" && (response.likelihood_grade || response.edge_estimate) && (
        <div className={styles.domainFields}>
          {response.likelihood_grade && (
            <div>
              <strong>Likelihood Grade:</strong> {response.likelihood_grade}
            </div>
          )}
          {response.edge_estimate !== undefined && (
            <div>
              <strong>Edge Estimate:</strong> {(response.edge_estimate * 100).toFixed(1)}%
            </div>
          )}
        </div>
      )}

      {domain === "crypto" && (
        <div className={styles.domainFields}>
          {response.pattern_frequency !== undefined && (
            <div>
              <strong>Pattern Frequency:</strong> {(response.pattern_frequency * 100).toFixed(0)}%
            </div>
          )}
          {response.failure_periods && response.failure_periods.length > 0 && (
            <div>
              <strong>Failed Periods:</strong> {response.failure_periods.join(", ")}
            </div>
          )}
          {response.remaining_edge !== undefined && (
            <div>
              <strong>Remaining Edge:</strong> {(response.remaining_edge * 100).toFixed(1)}%
            </div>
          )}
        </div>
      )}

      {domain === "stocks" && (
        <div className={styles.domainFields}>
          {response.correlation_grade && (
            <div>
              <strong>Correlation Grade:</strong> {response.correlation_grade}
            </div>
          )}
          {response.fundamentals_match !== undefined && (
            <div>
              <strong>Fundamentals Match:</strong> {response.fundamentals_match ? "Yes" : "No"}
            </div>
          )}
          {response.volume_analysis && (
            <div>
              <strong>Volume Analysis:</strong> {response.volume_analysis}
            </div>
          )}
        </div>
      )}

      {domain === "conspiracies" && (
        <div className={styles.domainFields}>
          {response.likelihood_rating !== undefined && (
            <div>
              <strong>Likelihood Rating:</strong> {response.likelihood_rating}/100
            </div>
          )}
          {response.evidence_for && response.evidence_for.length > 0 && (
            <div>
              <strong>Evidence For:</strong>
              <ul>
                {response.evidence_for.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {response.evidence_against && response.evidence_against.length > 0 && (
            <div>
              <strong>Evidence Against:</strong>
              <ul>
                {response.evidence_against.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {response.historical_parallels && response.historical_parallels.length > 0 && (
            <div>
              <strong>Historical Parallels:</strong>
              <ul>
                {response.historical_parallels.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {response.missing_data && response.missing_data.length > 0 && (
            <div>
              <strong>Missing Data:</strong>
              <ul>
                {response.missing_data.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
