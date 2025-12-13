import React from "react";
import styles from "../../../app/admin/theory-bets/eda/page.module.css";
import { type ExposureControls, type TargetDefinition } from "@/lib/api/sportsAdmin";

type Props = {
  exposureControls: ExposureControls;
  onChange: (next: ExposureControls) => void;
  targetDefinition: TargetDefinition;
};

export function ExposureControlsCard({ exposureControls, onChange, targetDefinition }: Props) {
  return (
    <div className={styles.sectionCard}>
      <h4 className={styles.sectionTitle}>Exposure controls</h4>
      <p className={styles.hint}>Applied after trigger logic to simulate “what would have been bet”.</p>
      <div className={styles.contextRow}>
        <label className={styles.inlineField}>
          Max bets/day
          <input
            className={styles.inputInline}
            type="number"
            min={0}
            step={1}
            value={exposureControls.max_bets_per_day ?? ""}
            onChange={(e) =>
              onChange({ ...exposureControls, max_bets_per_day: e.target.value === "" ? null : Number(e.target.value) })
            }
          />
        </label>
        <label className={styles.inlineField}>
          Max per side/day
          <input
            className={styles.inputInline}
            type="number"
            min={0}
            step={1}
            value={exposureControls.max_bets_per_side_per_day ?? ""}
            onChange={(e) =>
              onChange({
                ...exposureControls,
                max_bets_per_side_per_day: e.target.value === "" ? null : Number(e.target.value),
              })
            }
            placeholder="(off)"
          />
        </label>
        <label className={styles.inlineField}>
          Spread abs min
          <input
            className={styles.inputInline}
            type="number"
            step={0.5}
            value={exposureControls.spread_abs_min ?? ""}
            onChange={(e) =>
              onChange({ ...exposureControls, spread_abs_min: e.target.value === "" ? null : Number(e.target.value) })
            }
            placeholder="(off)"
            disabled={targetDefinition.market_type !== "spread"}
          />
        </label>
        <label className={styles.inlineField}>
          Spread abs max
          <input
            className={styles.inputInline}
            type="number"
            step={0.5}
            value={exposureControls.spread_abs_max ?? ""}
            onChange={(e) =>
              onChange({ ...exposureControls, spread_abs_max: e.target.value === "" ? null : Number(e.target.value) })
            }
            placeholder="(off)"
            disabled={targetDefinition.market_type !== "spread"}
          />
        </label>
      </div>
      <p className={styles.hint}>Selection ranks by edge (model_prob − implied_prob) within each day, then applies caps.</p>
    </div>
  );
}

