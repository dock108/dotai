"use client";

import React from "react";
import styles from "./TheoryBuilder.module.css";
import type { Target, TargetType, TargetSide } from "@/lib/api/theoryDraft";

interface Props {
  value: Target;
  onChange: (target: Target) => void;
}

const TARGET_OPTIONS: { type: TargetType; label: string; description: string }[] = [
  {
    type: "game_total",
    label: "Game total (points)",
    description: "Predict or analyze combined score",
  },
  {
    type: "spread_result",
    label: "Spread result",
    description: "Did the team cover the spread?",
  },
  {
    type: "moneyline_win",
    label: "Moneyline (W/L)",
    description: "Did the team win outright?",
  },
  {
    type: "team_stat",
    label: "Team stat outcome",
    description: "Analyze a specific team statistic",
  },
];

export function TargetSelector({ value, onChange }: Props) {
  const handleTypeChange = (type: TargetType) => {
    // Set sensible defaults based on type - side is always optional now
    let newTarget: Target;
    switch (type) {
      case "game_total":
        newTarget = { type, stat: "combined_score", metric: "numeric", side: null };
        break;
      case "spread_result":
        newTarget = { type, stat: "did_cover", metric: "binary", side: null };
        break;
      case "moneyline_win":
        newTarget = { type, stat: "winner", metric: "binary", side: null };
        break;
      case "team_stat":
        newTarget = { type, stat: null, metric: "numeric", side: null };
        break;
      default:
        newTarget = value;
    }
    onChange(newTarget);
  };

  // Side is optional for all market targets - only needed if theory is about home/away specifically
  const canHaveSide = value.type === "spread_result" || value.type === "moneyline_win";
  const needsStat = value.type === "team_stat";
  const sideOptions: { value: TargetSide | "any"; label: string }[] = [
    { value: "any", label: "Any (not side-specific)" },
    { value: "home", label: "Home" },
    { value: "away", label: "Away" },
  ];

  return (
    <div className={styles.targetSelector}>
      <div
        className={styles.targetOptions}
        role="radiogroup"
        aria-label="What are you trying to explain or predict?"
      >
        {TARGET_OPTIONS.map((opt) => {
          const isSelected = value.type === opt.type;
          return (
            <button
              key={opt.type}
              type="button"
              role="radio"
              aria-checked={isSelected}
              className={`${styles.targetOption} ${isSelected ? styles.targetOptionSelected : ""}`}
              onClick={() => handleTypeChange(opt.type)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleTypeChange(opt.type);
                }
              }}
            >
              <span className={styles.targetLabel}>{opt.label}</span>
              <span className={styles.targetDesc}>{opt.description}</span>
            </button>
          );
        })}
      </div>

      {canHaveSide && (
        <div className={styles.targetSecondary}>
          <label className={styles.fieldLabel}>
            Side (optional)
            <select
              className={styles.select}
              value={value.side ?? "any"}
              onChange={(e) => onChange({ 
                ...value, 
                side: e.target.value === "any" ? null : e.target.value as TargetSide 
              })}
            >
              {sideOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <p className={styles.sideHint}>
            Leave as "Any" unless your theory is specifically about home/away performance.
          </p>
        </div>
      )}

      {needsStat && (
        <div className={styles.targetSecondary}>
          <label className={styles.fieldLabel}>
            Stat name
            <input
              type="text"
              className={styles.input}
              placeholder="e.g., turnovers, fg3, ast"
              value={value.stat ?? ""}
              onChange={(e) => onChange({ ...value, stat: e.target.value || null })}
            />
          </label>
        </div>
      )}
    </div>
  );
}

