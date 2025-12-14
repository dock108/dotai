"use client";

import styles from "@/app/admin/theory-bets/eda/page.module.css";
import type { ModelBuildResponse } from "@/lib/api/sportsAdmin";

interface PublishingReadinessCardProps {
  modelResult: ModelBuildResponse;
  diagnosticMode: boolean;
  hasPostGameLeakage: boolean;
  anyAccepted: boolean;
  theoryDraftStatus: Record<string, "draft" | "accepted" | "rejected">;
  theoryDraftEdits: Record<string, string>;
  setTheoryDraftStatus: (fn: (prev: Record<string, "draft" | "accepted" | "rejected">) => Record<string, "draft" | "accepted" | "rejected">) => void;
  setTheoryDraftEdits: (fn: (prev: Record<string, string>) => Record<string, string>) => void;
}

export function PublishingReadinessCard({
  modelResult,
  diagnosticMode,
  hasPostGameLeakage,
  anyAccepted,
  theoryDraftStatus,
  theoryDraftEdits,
  setTheoryDraftStatus,
  setTheoryDraftEdits,
}: PublishingReadinessCardProps) {
  const blockers: string[] = [];
  const policy = modelResult.feature_policy;
  const anyRedZone =
    (modelResult.performance_slices?.confidence ?? []).some((s: any) => s.red_zone) ||
    (modelResult.performance_slices?.spread_buckets ?? []).some((s: any) => s.red_zone) ||
    (modelResult.performance_slices?.favorite_vs_underdog ?? []).some((s: any) => s.red_zone);
  if (diagnosticMode) blockers.push("Diagnostic mode is ON (must be deployable).");
  if (policy?.dropped_post_game_count > 0 || hasPostGameLeakage) blockers.push("Leakage present (post-game features).");
  if (anyRedZone) blockers.push("Unstable across slices (red zones present).");
  if (!anyAccepted) blockers.push("No human-approved theory framing (accept at least one candidate).");
  const ready = blockers.length === 0;

  return (
    <>
      <div className={styles.sectionCard}>
        <h4 className={styles.sectionTitle}>Publishing readiness</h4>
        <div className={styles.metricsGrid}>
          <div>
            Ready: <span className={styles.summaryValue}>{ready ? "Yes" : "No"}</span>
          </div>
          <div>
            Blockers: <span className={styles.summaryValue}>{blockers.length}</span>
          </div>
        </div>
        {blockers.length > 0 ? (
          <ul className={styles.insightsList}>
            {blockers.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        ) : (
          <p className={styles.hint}>All checklist items satisfied for publishing readiness.</p>
        )}
      </div>

      <div className={styles.featureList}>
        {Object.entries(modelResult.model_summary.feature_weights).map(([name, weight]) => (
          <div key={name} className={styles.featureItem}>
            <div className={styles.featureName}>{name}</div>
            <div className={styles.featureFormula}>weight: {weight.toFixed(3)}</div>
          </div>
        ))}
      </div>

      <h4 className={styles.sectionTitle}>Suggested theories</h4>
      {modelResult.suggested_theories.length === 0 && <p className={styles.hint}>No theories generated.</p>}
      {modelResult.suggested_theories.length > 0 && (
        <div className={styles.theoryList}>
          {modelResult.suggested_theories.map((t, idx) => (
            <div key={idx} className={styles.featureItem}>
              <div className={styles.featureName}>{t.text}</div>
              <div className={styles.hint}>Confidence: {t.confidence}</div>
              <div className={styles.hint}>Edge: {(t.historical_edge * 100).toFixed(1)}%</div>
            </div>
          ))}
        </div>
      )}

      <h4 className={styles.sectionTitle}>Suggested theories (candidates)</h4>
      {!modelResult.theory_candidates || modelResult.theory_candidates.length === 0 ? (
        <p className={styles.hint}>No candidates met thresholds (sample size + lift).</p>
      ) : (
        <div className={styles.theoryList}>
          {modelResult.theory_candidates.map((c: any, idx: number) => {
            const key = String(c.condition ?? idx);
            const draft = theoryDraftEdits[key] ?? String(c.framing_draft ?? "");
            const status = theoryDraftStatus[key] ?? "draft";
            return (
              <div key={key} className={styles.featureItem}>
                <div className={styles.featureName}>
                  {status === "accepted" ? "ACCEPTED: " : status === "rejected" ? "REJECTED: " : ""}
                  {String(c.condition ?? "—")}
                </div>
                <div className={styles.hint}>
                  Sample: {Number(c.sample_size ?? 0).toLocaleString()} · Lift:{" "}
                  {c.lift != null ? `${(Number(c.lift) * 100).toFixed(1)}%` : "—"} · Hit:{" "}
                  {c.hit_rate != null ? `${(Number(c.hit_rate) * 100).toFixed(1)}%` : "—"} · Baseline:{" "}
                  {c.baseline_rate != null ? `${(Number(c.baseline_rate) * 100).toFixed(1)}%` : "—"}
                </div>
                <textarea
                  className={styles.textarea}
                  value={draft}
                  onChange={(e) => setTheoryDraftEdits((prev) => ({ ...prev, [key]: e.target.value }))}
                  rows={3}
                />
                <div className={styles.previewActions}>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => setTheoryDraftStatus((prev) => ({ ...prev, [key]: "accepted" }))}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => setTheoryDraftStatus((prev) => ({ ...prev, [key]: "rejected" }))}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    className={styles.linkButton}
                    onClick={() => {
                      setTheoryDraftEdits((prev) => {
                        const next = { ...prev };
                        delete next[key];
                        return next;
                      });
                      setTheoryDraftStatus((prev) => ({ ...prev, [key]: "draft" }));
                    }}
                  >
                    Reset
                  </button>
                </div>
                <p className={styles.hint}>Read-only for now (not persisted). User must confirm or reject.</p>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}

