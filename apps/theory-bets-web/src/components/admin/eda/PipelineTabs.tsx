import React from "react";
import styles from "@/app/admin/theory-bets/eda/page.module.css";

export type PipelineStep = "theory" | "cohort" | "evaluation" | "market" | "modeling" | "mc" | "walk" | "live";

type Props = {
  step: PipelineStep;
  onChange: (step: PipelineStep) => void;
};

const PIPELINE_STEPS: Array<[PipelineStep, string]> = [
  ["theory", "1. Theory Definition"],
  ["cohort", "2. Cohort & Micro"],
  ["evaluation", "3. Evaluation"],
  ["market", "4. Market Mapping"],
  ["modeling", "5. Modeling"],
  ["mc", "6. Robustness MC"],
  ["walk", "7. Walk-forward"],
  ["live", "8. Live Matches"],
];

export function PipelineTabs({ step, onChange }: Props) {
  return (
    <div className={styles.pipelineTabs}>
      {PIPELINE_STEPS.map(([id, label]) => (
        <button
          key={id}
          type="button"
          className={`${styles.tabButton} ${step === id ? styles.tabActive : ""}`}
          onClick={() => onChange(id)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

