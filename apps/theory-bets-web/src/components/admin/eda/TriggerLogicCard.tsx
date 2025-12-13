import React from "react";
import styles from "../../../app/admin/theory-bets/eda/page.module.css";
import { type TriggerDefinition } from "@/lib/api/sportsAdmin";

type Props = {
  triggerDefinition: TriggerDefinition;
  onChange: (next: TriggerDefinition) => void;
};

export function TriggerLogicCard({ triggerDefinition, onChange }: Props) {
  return (
    <div className={styles.sectionCard}>
      <h4 className={styles.sectionTitle}>Trigger logic</h4>
      <p className={styles.hint}>Used only after “Build model” (requires model probability).</p>
      <div className={styles.contextRow}>
        <label className={styles.inlineField}>
          Prob threshold
          <input
            className={styles.inputInline}
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={triggerDefinition.prob_threshold}
            onChange={(e) => onChange({ ...triggerDefinition, prob_threshold: Number(e.target.value) })}
          />
        </label>
        <label className={styles.inlineField}>
          Confidence band (|p-0.5|)
          <input
            className={styles.inputInline}
            type="number"
            min={0}
            max={0.5}
            step={0.01}
            value={triggerDefinition.confidence_band ?? ""}
            onChange={(e) =>
              onChange({
                ...triggerDefinition,
                confidence_band: e.target.value === "" ? null : Number(e.target.value),
              })
            }
            placeholder="(off)"
          />
        </label>
        <label className={styles.inlineField}>
          Min edge vs implied
          <input
            className={styles.inputInline}
            type="number"
            min={-1}
            max={1}
            step={0.01}
            value={triggerDefinition.min_edge_vs_implied ?? ""}
            onChange={(e) =>
              onChange({
                ...triggerDefinition,
                min_edge_vs_implied: e.target.value === "" ? null : Number(e.target.value),
              })
            }
            placeholder="(off)"
          />
        </label>
      </div>
      <div className={styles.hint}>
        Trigger = model_prob ≥ {triggerDefinition.prob_threshold.toFixed(2)}
        {triggerDefinition.confidence_band != null ? ` and |p-0.5| ≥ ${triggerDefinition.confidence_band.toFixed(2)}` : ""}{" "}
        {triggerDefinition.min_edge_vs_implied != null ? ` and edge ≥ ${triggerDefinition.min_edge_vs_implied.toFixed(2)}` : ""}
      </div>
    </div>
  );
}

