import React, { useMemo } from "react";
import styles from "../../../app/admin/theory-bets/eda/page.module.css";
import { type TargetDefinition } from "@/lib/api/sportsAdmin";

type Props = {
  targetDefinition: TargetDefinition;
  targetLocked: boolean;
  onChange: (next: TargetDefinition) => void;
  onToggleLock: () => void;
};

export function TargetDefinitionCard({ targetDefinition, targetLocked, onChange, onToggleLock }: Props) {
  const STAT_TARGETS: { label: string; value: TargetDefinition["target_name"]; metric: TargetDefinition["metric_type"] }[] = useMemo(
    () => [
      { label: "Home points", value: "home_points", metric: "numeric" },
      { label: "Away points", value: "away_points", metric: "numeric" },
      { label: "Combined score", value: "combined_score", metric: "numeric" },
      { label: "Margin of victory", value: "margin_of_victory", metric: "numeric" },
      { label: "Winner (binary)", value: "winner", metric: "binary" },
    ],
    []
  );

  const MARKET_TARGETS: { label: string; value: string; market_type: "spread" | "total" | "moneyline"; metric: "binary" }[] = useMemo(
    () => [
      { label: "ATS cover", value: "ats_cover", market_type: "spread", metric: "binary" },
      { label: "Moneyline win", value: "moneyline_win", market_type: "moneyline", metric: "binary" },
      { label: "Total over hit", value: "total_over_hit", market_type: "total", metric: "binary" },
    ],
    []
  );

  const isMarket = targetDefinition.target_class === "market";
  const currentMetric = targetDefinition.metric_type;
  const currentMarketTarget = MARKET_TARGETS.find((m) => m.value === targetDefinition.target_name);

  return (
    <div className={styles.sectionCard}>
      <h4 className={styles.sectionTitle}>Target definition</h4>
      <p className={styles.hint}>Lock target before running. Targets measure behavior; markets monetize behavior.</p>
      <div className={styles.contextRow}>
        <label className={styles.inlineField}>
          Target class
          <select
            className={styles.select}
            value={targetDefinition.target_class}
            disabled={targetLocked}
            onChange={(e) => {
              const cls = e.target.value as TargetDefinition["target_class"];
              if (cls === "stat") {
                const def: TargetDefinition = {
                  target_class: "stat",
                  target_name: "combined_score",
                  metric_type: "numeric",
                  odds_required: false,
                };
                onChange(def);
              } else {
                const def: TargetDefinition = {
                  target_class: "market",
                  target_name: "ats_cover",
                  metric_type: "binary",
                  market_type: "spread",
                  side: "home",
                  odds_required: true,
                };
                onChange(def);
              }
            }}
          >
            <option value="stat">Stat</option>
            <option value="market">Market</option>
          </select>
        </label>
        <label className={styles.inlineField}>
          Target
          <select
            className={styles.select}
            value={targetDefinition.target_name}
            disabled={targetLocked}
            onChange={(e) => {
              const val = e.target.value;
              if (!isMarket) {
                const opt = STAT_TARGETS.find((t) => t.value === val) ?? STAT_TARGETS[0];
                onChange({
                  target_class: "stat",
                  target_name: opt.value,
                  metric_type: opt.metric,
                  odds_required: false,
                });
              } else {
                const opt = MARKET_TARGETS.find((t) => t.value === val) ?? MARKET_TARGETS[0];
                const nextSide = opt.market_type === "total" ? "over" : "home";
                onChange({
                  target_class: "market",
                  target_name: opt.value,
                  metric_type: opt.metric,
                  market_type: opt.market_type,
                  side: targetDefinition.side && targetDefinition.market_type === opt.market_type ? targetDefinition.side : nextSide,
                  odds_required: true,
                });
              }
            }}
          >
            {isMarket
              ? MARKET_TARGETS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))
              : STAT_TARGETS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
          </select>
        </label>
        <label className={styles.inlineField}>
          Metric
          <input className={styles.input} value={currentMetric} readOnly disabled />
        </label>

        {isMarket && (
          <>
            <label className={styles.inlineField}>
              Market
              <select
                className={styles.select}
                value={targetDefinition.market_type}
                disabled={targetLocked}
                onChange={(e) => {
                  const mt = e.target.value as NonNullable<TargetDefinition["market_type"]>;
                  const next = MARKET_TARGETS.find((m) => m.market_type === mt) ?? currentMarketTarget ?? MARKET_TARGETS[0];
                  const side = mt === "total" ? "over" : "home";
                  onChange({
                    target_class: "market",
                    target_name: next.value,
                    metric_type: "binary",
                    market_type: mt,
                    side,
                    odds_required: true,
                  });
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
                onChange={(e) => onChange({ ...targetDefinition, side: e.target.value as NonNullable<TargetDefinition["side"]> })}
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
          </>
        )}

        <button type="button" className={styles.secondaryButton} onClick={onToggleLock}>
          {targetLocked ? "Unlock target" : "Lock target"}
        </button>
      </div>
      <div className={styles.hint}>
        Locked: <span className={styles.summaryValue}>{targetLocked ? "Yes" : "No"}</span> · {targetDefinition.target_class} · {targetDefinition.target_name} ·{" "}
        {isMarket ? `${targetDefinition.market_type}/${targetDefinition.side}` : "stat-only"}
      </div>
    </div>
  );
}

