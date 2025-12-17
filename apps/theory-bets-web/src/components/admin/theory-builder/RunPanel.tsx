"use client";

import React from "react";
import styles from "./TheoryBuilder.module.css";
import type { TheoryBuilderState, TheoryBuilderActions } from "./useTheoryBuilderState";

interface Props {
  state: TheoryBuilderState;
  actions: TheoryBuilderActions;
}

export function RunPanel({ state, actions }: Props) {
  const {
    draft,
    analysisResult,
    analysisLoading,
    analysisError,
    modelLoading,
    modelError,
    mcLoading,
    mcError,
  } = state;

  const hasAnalysis = !!analysisResult;
  const canModel = hasAnalysis && analysisResult.modeling_available;
  const canMC = hasAnalysis && analysisResult.mc_available;

  return (
    <div className={styles.runPanel}>
      <div className={styles.statusSection}>
        <h3 className={styles.sectionTitle}>Status</h3>
        {analysisError && (
          <div className={styles.errorMessage}>{analysisError}</div>
        )}
        {modelError && (
          <div className={styles.errorMessage}>{modelError}</div>
        )}
        {mcError && (
          <div className={styles.errorMessage}>{mcError}</div>
        )}

        {hasAnalysis ? (
          <div className={styles.statusCard}>
            <div className={styles.statusRow}>
              <span className={styles.statusLabel}>Sample size</span>
              <span className={styles.statusValue}>
                {analysisResult.sample_size.toLocaleString()}
              </span>
            </div>
            <div className={styles.statusRow}>
              <span className={styles.statusLabel}>Baseline</span>
              <span className={styles.statusValue}>
                {analysisResult.baseline_value.toFixed(2)}
              </span>
            </div>
            {analysisResult.cohort_value != null && (
              <div className={styles.statusRow}>
                <span className={styles.statusLabel}>Cohort mean</span>
                <span className={styles.statusValue}>
                  {analysisResult.cohort_value.toFixed(2)}
                </span>
              </div>
            )}
            {analysisResult.delta_value != null && (
              <div className={styles.statusRow}>
                <span className={styles.statusLabel}>Delta</span>
                <span className={styles.statusValue}>
                  {analysisResult.delta_value.toFixed(2)}
                </span>
              </div>
            )}
            {analysisResult.detected_concepts.length > 0 && (
              <div className={styles.conceptsBox}>
                <span className={styles.conceptsLabel}>Detected concepts:</span>
                <span className={styles.conceptsList}>
                  {analysisResult.detected_concepts.join(", ")}
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className={styles.statusCard}>
            <p className={styles.hint}>
              Run analysis to see results. Configure your theory in the Define tab.
            </p>
          </div>
        )}
      </div>

      <div className={styles.actionsSection}>
        <h3 className={styles.sectionTitle}>Actions</h3>
        <div className={styles.actionButtons}>
          <button
            type="button"
            className={styles.primaryButton}
            disabled={analysisLoading || draft.inputs.base_stats.length === 0}
            onClick={actions.runAnalysis}
          >
            {analysisLoading ? "Analyzing…" : "Run Analysis"}
          </button>

          <button
            type="button"
            className={styles.secondaryButton}
            disabled={!canModel || modelLoading}
            onClick={actions.runModel}
            title={!canModel ? "Run analysis first" : undefined}
          >
            {modelLoading ? "Building…" : "Build Model"}
          </button>

          <button
            type="button"
            className={styles.tertiaryButton}
            disabled={!canMC || mcLoading}
            onClick={actions.runMonteCarlo}
            title={
              !canMC
                ? analysisResult?.mc_reason ?? "Monte Carlo not available"
                : undefined
            }
          >
            {mcLoading ? "Running…" : "Monte Carlo"}
          </button>
        </div>

        {!canMC && hasAnalysis && analysisResult.mc_reason && (
          <p className={styles.actionHint}>
            MC unavailable: {analysisResult.mc_reason}
          </p>
        )}
      </div>

      {hasAnalysis && analysisResult.notes.length > 0 && (
        <div className={styles.notesSection}>
          <h3 className={styles.sectionTitle}>Notes</h3>
          <ul className={styles.notesList}>
            {analysisResult.notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

