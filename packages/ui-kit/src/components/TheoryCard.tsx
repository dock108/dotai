"use client";

import { useState } from "react";
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

function DomainSection({ title, children, response }: { title: string; children: React.ReactNode; response: TheoryResponse }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className={styles.domainSection}>
      <button
        className={styles.domainSectionHeader}
        onClick={() => setExpanded(!expanded)}
        type="button"
      >
        <h4 className={styles.domainSectionTitle}>{title}</h4>
        <span className={styles.toggleIcon}>{expanded ? "−" : "+"}</span>
      </button>
      {expanded && <div className={styles.domainSectionContent}>{children}</div>}
    </div>
  );
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

      {/* Domain-specific fields with collapsible sections */}
      {domain === "bets" && (response.likelihood_grade || response.edge_estimate || response.kelly_sizing_example) && (
        <DomainSection title="Betting Analysis" response={response}>
          {response.likelihood_grade && (
            <div className={styles.domainField}>
              <strong>Likelihood Grade:</strong> <span className={styles.grade}>{response.likelihood_grade}</span>
            </div>
          )}
          {response.edge_estimate !== undefined && response.edge_estimate !== null && (
            <div className={styles.domainField}>
              <strong>Edge Estimate:</strong> <span className={styles.positive}>{(response.edge_estimate * 100).toFixed(1)}%</span>
            </div>
          )}
          {response.kelly_sizing_example && (
            <div className={styles.domainField}>
              <strong>Kelly Sizing Example:</strong>
              <p className={styles.exampleText}>{response.kelly_sizing_example}</p>
            </div>
          )}
        </DomainSection>
      )}

      {domain === "crypto" && (response.pattern_frequency !== undefined || response.failure_periods?.length || response.remaining_edge !== undefined) && (
        <DomainSection title="Pattern Analysis" response={response}>
          {response.pattern_frequency !== undefined && (
            <div className={styles.domainField}>
              <strong>Pattern Frequency:</strong> <span className={styles.percentage}>{(response.pattern_frequency * 100).toFixed(0)}%</span>
            </div>
          )}
          {response.failure_periods && response.failure_periods.length > 0 && (
            <div className={styles.domainField}>
              <strong>Failed Periods:</strong>
              <ul className={styles.domainList}>
                {response.failure_periods.map((period, idx) => (
                  <li key={idx}>{period}</li>
                ))}
              </ul>
            </div>
          )}
          {response.remaining_edge !== undefined && response.remaining_edge !== null && (
            <div className={styles.domainField}>
              <strong>Remaining Edge:</strong> <span className={response.remaining_edge > 0 ? styles.positive : styles.negative}>
                {(response.remaining_edge * 100).toFixed(1)}%
              </span>
            </div>
          )}
        </DomainSection>
      )}

      {domain === "stocks" && (response.correlation_grade || response.fundamentals_match !== undefined || response.volume_analysis) && (
        <DomainSection title="Fundamentals Analysis" response={response}>
          {response.correlation_grade && (
            <div className={styles.domainField}>
              <strong>Correlation Grade:</strong> <span className={styles.grade}>{response.correlation_grade}</span>
            </div>
          )}
          {response.fundamentals_match !== undefined && (
            <div className={styles.domainField}>
              <strong>Fundamentals Match:</strong> <span className={response.fundamentals_match ? styles.positive : styles.negative}>
                {response.fundamentals_match ? "Yes" : "No"}
              </span>
            </div>
          )}
          {response.volume_analysis && (
            <div className={styles.domainField}>
              <strong>Volume Analysis:</strong>
              <p className={styles.analysisText}>{response.volume_analysis}</p>
            </div>
          )}
        </DomainSection>
      )}

      {domain === "conspiracies" && (
        <DomainSection title="Fact-Checking Analysis" response={response}>
          {response.likelihood_rating !== undefined && (
            <div className={styles.domainField}>
              <strong>Likelihood Rating:</strong> <span className={styles.rating}>{response.likelihood_rating}/100</span>
            </div>
          )}
          {response.evidence_for && response.evidence_for.length > 0 && (
            <div className={styles.domainField}>
              <strong>Evidence For:</strong>
              <ul className={styles.domainList}>
                {response.evidence_for.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {response.evidence_against && response.evidence_against.length > 0 && (
            <div className={styles.domainField}>
              <strong>Evidence Against:</strong>
              <ul className={styles.domainList}>
                {response.evidence_against.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {response.historical_parallels && response.historical_parallels.length > 0 && (
            <div className={styles.domainField}>
              <strong>Historical Parallels:</strong>
              <ul className={styles.domainList}>
                {response.historical_parallels.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {response.missing_data && response.missing_data.length > 0 && (
            <div className={styles.domainField}>
              <strong>Missing Data:</strong>
              <ul className={styles.domainList}>
                {response.missing_data.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </DomainSection>
      )}
    </div>
  );
}
