"""Generate simple natural-language theories from model signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Sequence, Any
from .model_builder import TrainedModel


@dataclass
class SuggestedTheory:
    text: str
    features_used: List[str]
    historical_edge: float
    confidence: str  # "high", "medium", "exploratory"


def generate_theories(
    model: TrainedModel,
    correlations: Sequence[Mapping[str, object]],
    segments: Sequence[Mapping[str, object]],
    target_def: Any,
    sample_size: int,
) -> List[SuggestedTheory]:
    theories: List[SuggestedTheory] = []

    # Use top correlations to craft statements
    def _corr_val(c: Mapping[str, object]) -> float:
        try:
            return float(c.get("correlation", 0.0))  # type: ignore[arg-type]
        except Exception:
            return 0.0

    target_name = ""
    try:
        if hasattr(target_def, "target_name"):
            target_name = target_def.target_name
        elif isinstance(target_def, dict):
            target_name = str(target_def.get("target_name", "target"))
    except Exception:
        target_name = "target"

    top_corr = sorted(correlations, key=lambda c: abs(_corr_val(c)), reverse=True)[:3]
    for corr in top_corr:
        corr_val = _corr_val(corr)
        direction = "increase" if corr_val > 0 else "decrease"
        confidence = "high" if abs(corr_val) > 0.12 else "medium" if abs(corr_val) > 0.07 else "exploratory"
        feature_name = str(corr.get("feature", "feature"))
        theories.append(
            SuggestedTheory(
                text=(
                    f"Hypothesis: When {feature_name} tends to {direction}, the target '{target_name}' shifts in that direction "
                    f"(sample n={sample_size}, |corr|≈{abs(corr_val):.3f})."
                ),
                features_used=[feature_name],
                historical_edge=abs(corr_val),
                confidence=confidence,
            )
        )

    # Use best segments if present
    for seg in list(segments)[:2]:
        try:
            edge_val = float(seg.get("edge", 0.0))  # type: ignore[arg-type]
        except Exception:
            edge_val = 0.0
        confidence = "high" if edge_val > 0.08 else "medium" if edge_val > 0.04 else "exploratory"
        condition = str(seg.get("condition", "segment"))
        theories.append(
            SuggestedTheory(
                text=(
                    f"Hypothesis: Condition '{condition}' shows directional difference vs baseline for '{target_name}' "
                    f"(sample n={sample_size}, directional lift proxy≈{edge_val:.3f})."
                ),
                features_used=[],
                historical_edge=edge_val,
                confidence=confidence,
            )
        )

    return theories

