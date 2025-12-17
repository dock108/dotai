import React from "react";
import styles from "../../../app/admin/theory-bets/eda/page.module.css";
import { type GeneratedFeature } from "@/lib/api/sportsAdmin";

type Props = {
  features: GeneratedFeature[];
  selectedFeatureNames: Set<string>;
  onToggleFeature: (name: string) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
  onSelectByCategory: (category: string) => void;
  featureSummary: string | null;
  featureError: string | null;
  featureLeakageSummary: { postGameCount: number; hasPostGame: boolean };
  featurePolicyMessage: string | null;
};

export function FeatureListPanel({
  features,
  selectedFeatureNames,
  onToggleFeature,
  onSelectAll,
  onSelectNone,
  onSelectByCategory,
  featureSummary,
  featureError,
  featureLeakageSummary,
  featurePolicyMessage,
}: Props) {
  const categories = Array.from(new Set(features.map((f) => f.category))).sort();

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

      {features.length === 0 ? (
        <div className={styles.sectionCard}>
          <h4 className={styles.sectionTitle}>Explanatory features (optional)</h4>
          <div className={styles.hint}>
            No feature catalog yet. Run <b>Add explanatory features</b> after Analyze to populate the selectable list (pace, conference, player minutes, rolling, etc.).
          </div>
        </div>
      ) : (
        <details className={styles.advanced}>
          <summary>
            Explanatory features (collapsed) · Selected:{" "}
            <span className={styles.summaryValue}>{selectedFeatureNames.size.toLocaleString()}</span> /{" "}
            <span className={styles.summaryValue}>{features.length.toLocaleString()}</span>
          </summary>
          <div className={styles.hint} style={{ marginTop: 8 }}>
            Want to explore why this works? Add optional explanatory features below. Analysis already ran without them.
          </div>
          <div className={styles.contextRow} style={{ marginTop: 8 }}>
            <button type="button" className={styles.secondaryButton} onClick={onSelectAll}>
              Select all
            </button>
            <button type="button" className={styles.secondaryButton} onClick={onSelectNone}>
              Select none
            </button>
            {categories.map((cat) => (
              <button key={cat} type="button" className={styles.secondaryButton} onClick={() => onSelectByCategory(cat)}>
                Select {cat}
              </button>
            ))}
          </div>
          <div className={styles.featureList}>
            {features.map((f) => (
              <div key={f.name} className={styles.featureItem}>
                <label className={styles.toggle} style={{ alignItems: "flex-start" }}>
                  <input
                    type="checkbox"
                    checked={selectedFeatureNames.has(f.name)}
                    onChange={() => onToggleFeature(f.name)}
                  />
                  <div>
                <div className={styles.featureName}>{f.name}</div>
                <div className={styles.featureFormula}>{f.formula}</div>
                <div className={styles.featureMeta}>
                  {f.category}
                  {f.timing ? ` · ${f.timing}` : ""}
                  {f.group ? ` · ${f.group}` : ""}
                </div>
                  </div>
                </label>
              </div>
            ))}
          </div>
        </details>
      )}
    </>
  );
}

