from __future__ import annotations

from typing import Any, List

import numpy as np


def generate_theory_candidates(
    aligned_rows: List[dict[str, float]],
    feature_names: List[str],
    *,
    baseline_rate: float,
    target_def: dict[str, Any],
    min_sample_size: int = 150,
    min_lift: float = 0.02,
) -> List[dict[str, Any]]:
    if not aligned_rows or not feature_names:
        return []
    y = np.array([float(r.get("__target__", 0.0)) for r in aligned_rows], dtype=float)
    if len(y) < min_sample_size:
        return []
    candidates: List[dict[str, Any]] = []
    for fname in feature_names[: min(25, len(feature_names))]:
        vals = np.array([float(r.get(fname, 0.0)) for r in aligned_rows], dtype=float)
        if np.std(vals) < 1e-9:
            continue
        q25 = float(np.quantile(vals, 0.25))
        q75 = float(np.quantile(vals, 0.75))
        mean1 = float(np.mean(vals[y >= 0.5])) if np.any(y >= 0.5) else 0.0
        mean0 = float(np.mean(vals[y < 0.5])) if np.any(y < 0.5) else 0.0
        positive = mean1 >= mean0
        if positive:
            mask = vals >= q75
            condition = f"{fname} ≥ {q75:.3f}"
        else:
            mask = vals <= q25
            condition = f"{fname} ≤ {q25:.3f}"
        sample = int(np.sum(mask))
        if sample < min_sample_size:
            continue
        hit = float(np.mean(y[mask])) if sample else 0.0
        lift = hit - float(baseline_rate)
        if abs(lift) < min_lift:
            continue
        framing = (
            f"When {condition}, {target_def.get('market_type')}:{target_def.get('side')} outperforms baseline by {(lift*100):.1f}% "
            f"over {sample} bets."
        )
        candidates.append(
            {
                "condition": condition,
                "sample_size": sample,
                "hit_rate": hit,
                "baseline_rate": baseline_rate,
                "lift": lift,
                "framing_draft": framing,
                "status": "draft",
            }
        )
    candidates.sort(key=lambda c: (abs(float(c.get("lift") or 0.0)), int(c.get("sample_size") or 0)), reverse=True)
    return candidates[:10]


