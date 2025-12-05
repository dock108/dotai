"""Generate simple natural-language theories from model signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Sequence
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
) -> List[SuggestedTheory]:
    theories: List[SuggestedTheory] = []

    # Use top correlations to craft statements
    def _corr_val(c: Mapping[str, object]) -> float:
        try:
            return float(c.get("correlation", 0.0))  # type: ignore[arg-type]
        except Exception:
            return 0.0

    top_corr = sorted(correlations, key=lambda c: abs(_corr_val(c)), reverse=True)[:3]
    for corr in top_corr:
        corr_val = _corr_val(corr)
        direction = "increase" if corr_val > 0 else "decrease"
        confidence = "high" if abs(corr_val) > 0.12 else "medium" if abs(corr_val) > 0.07 else "exploratory"
        feature_name = str(corr.get("feature", "feature"))
        theories.append(
            SuggestedTheory(
                text=f"Outcomes improve when {feature_name} tends to {direction}.",
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
                text=f"Segment '{condition}' shows edge of {(edge_val*100):.1f}% on target.",
                features_used=[],
                historical_edge=edge_val,
                confidence=confidence,
            )
        )

    return theories

