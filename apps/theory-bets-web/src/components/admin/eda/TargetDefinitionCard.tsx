import React from "react";
import styles from "../../../app/admin/theory-bets/eda/page.module.css";
import { type TargetDefinition } from "@/lib/api/sportsAdmin";

type Props = {
  targetDefinition: TargetDefinition;
  targetLocked: boolean;
  onChange: (next: TargetDefinition) => void;
  onToggleLock: () => void;
};

export function TargetDefinitionCard({ targetDefinition, targetLocked, onChange, onToggleLock }: Props) {
  return (
    <div className={styles.sectionCard}>
      <h4 className={styles.sectionTitle}>Target definition</h4>
      <p className={styles.hint}>No analysis/model build runs unless the target is locked.</p>
      <div className={styles.contextRow}>
        <label className={styles.inlineField}>
          Market
          <select
            className={styles.select}
            value={targetDefinition.market_type}
            disabled={targetLocked}
            onChange={(e) => {
              const market = e.target.value as TargetDefinition["market_type"];
              onChange(
                (() => {
                  const next: TargetDefinition = { ...targetDefinition, market_type: market };
                  if (market === "total" && (next.side === "home" || next.side === "away")) next.side = "over";
                  if (market !== "total" && (next.side === "over" || next.side === "under")) next.side = "home";
                  return next;
                })()
              );
            }}
          >
            <option value="spread">Spread</option>
            <option value="total">Total</option>
            <option value="moneyline">Moneyline</option>
          </select>
        </label>
        <label className={styles.inlineField}>
          Side
          <select
            className={styles.select}
            value={targetDefinition.side}
            disabled={targetLocked}
            onChange={(e) => onChange({ ...targetDefinition, side: e.target.value as TargetDefinition["side"] })}
          >
            {targetDefinition.market_type === "total" ? (
              <>
                <option value="over">Over</option>
                <option value="under">Under</option>
              </>
            ) : (
              <>
                <option value="home">Home</option>
                <option value="away">Away</option>
              </>
            )}
          </select>
        </label>
        <label className={styles.inlineField}>
          Odds assumption
          <select
            className={styles.select}
            value={targetDefinition.odds_assumption ?? "use_closing"}
            disabled={targetLocked}
            onChange={(e) =>
              onChange({
                ...targetDefinition,
                odds_assumption: e.target.value as NonNullable<TargetDefinition["odds_assumption"]>,
              })
            }
          >
            <option value="use_closing">Use closing odds</option>
            <option value="flat_-110">Flat -110 (diagnostic)</option>
          </select>
        </label>
        <button type="button" className={styles.secondaryButton} onClick={onToggleLock}>
          {targetLocked ? "Unlock target" : "Lock target"}
        </button>
      </div>
      <div className={styles.hint}>
        Locked: <span className={styles.summaryValue}>{targetLocked ? "Yes" : "No"}</span> · {targetDefinition.market_type} · {targetDefinition.side} ·{" "}
        {targetDefinition.odds_assumption ?? "use_closing"}
      </div>
    </div>
  );
}

