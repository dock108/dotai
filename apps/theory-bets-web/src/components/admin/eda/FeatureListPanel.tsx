import React from "react";
import styles from "../../../app/admin/theory-bets/eda/page.module.css";
import { type GeneratedFeature } from "@/lib/api/sportsAdmin";

type Props = {
  features: GeneratedFeature[];
  featureSummary: string | null;
  featureError: string | null;
  featureLeakageSummary: { postGameCount: number; hasPostGame: boolean };
  featurePolicyMessage: string | null;
};

export function FeatureListPanel({
  features,
  featureSummary,
  featureError,
  featureLeakageSummary,
  featurePolicyMessage,
}: Props) {
  return (
    <>
      {featureLeakageSummary.hasPostGame && (
        <div className={styles.warning}>
          Contains post-game features (diagnostic only). Post-game count: {featureLeakageSummary.postGameCount.toLocaleString()}
        </div>
      )}
      {featurePolicyMessage && <div className={styles.warning}>{featurePolicyMessage}</div>}
      {featureError && <div className={styles.error}>{featureError}</div>}
      {featureSummary && <div className={styles.featureSummary}>{featureSummary}</div>}

      {features.length > 0 && (
        <details className={styles.advanced}>
          <summary>Feature list (collapsed)</summary>
          <div className={styles.featureList}>
            {features.map((f) => (
              <div key={f.name} className={styles.featureItem}>
                <div className={styles.featureName}>{f.name}</div>
                <div className={styles.featureFormula}>{f.formula}</div>
                <div className={styles.featureMeta}>
                  {f.category}
                  {f.timing ? ` · ${f.timing}` : ""}
                  {f.group ? ` · ${f.group}` : ""}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </>
  );
}

