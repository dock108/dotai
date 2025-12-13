from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np


def prune_feature_matrix(
    aligned_features: Dict[str, List[float]],
    feature_names: List[str],
    *,
    near_zero_weight_eps: float = 1e-6,
    collinearity_threshold: float = 0.98,
    max_features_for_collinearity: int = 600,
) -> Tuple[List[str], List[dict[str, Any]]]:
    """
    Stage 1.3: Automated pruning pass (structure only, no behavior change).
    """
    dropped: List[dict[str, Any]] = []

    kept: List[str] = []
    seen_signatures: set[tuple] = set()
    for name in feature_names:
        values = aligned_features.get(name, [])
        if not values:
            dropped.append({"feature": name, "reason": "missing_column"})
            continue
        clean = [v for v in values if not np.isnan(v)]
        if len(clean) < 5:
            dropped.append({"feature": name, "reason": "too_few_values", "non_nan": len(clean)})
            continue
        if float(np.std(clean)) < 1e-9:
            dropped.append({"feature": name, "reason": "near_constant"})
            continue
        signature = tuple(None if np.isnan(v) else round(float(v), 6) for v in values)
        if signature in seen_signatures:
            dropped.append({"feature": name, "reason": "duplicate_vector"})
            continue
        seen_signatures.add(signature)
        kept.append(name)

    if len(kept) > 1:
        subset = kept[:max_features_for_collinearity]
        drop_set: set[str] = set()
        for i in range(len(subset)):
            a = subset[i]
            if a in drop_set:
                continue
            xa = np.array(aligned_features[a], dtype=float)
            if np.isnan(xa).any():
                mu = float(np.nanmean(xa))
                xa = np.where(np.isnan(xa), mu, xa)
            for j in range(i + 1, len(subset)):
                b = subset[j]
                if b in drop_set:
                    continue
                xb = np.array(aligned_features[b], dtype=float)
                if np.isnan(xb).any():
                    mu = float(np.nanmean(xb))
                    xb = np.where(np.isnan(xb), mu, xb)
                if float(np.std(xa)) < 1e-9 or float(np.std(xb)) < 1e-9:
                    continue
                corr = float(np.corrcoef(xa, xb)[0, 1])
                if abs(corr) >= collinearity_threshold:
                    drop_set.add(b)
                    dropped.append(
                        {
                            "feature": b,
                            "reason": "near_collinear",
                            "with": a,
                            "abs_corr": abs(corr),
                            "threshold": collinearity_threshold,
                        }
                    )
        kept = [f for f in kept if f not in drop_set]

    return kept, dropped


