"""Lightweight concept detection for EDA Analyze.

Detects referenced concepts from theory context and returns the minimal
auto-derived fields needed to support them.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from .field_layers import CONCEPT_REGISTRY


def _text_matches(text: str | None, needles: Iterable[str]) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(n in lower for n in needles)


def detect_concepts(theory_text: str | None = None, filters: Mapping[str, object] | None = None) -> dict[str, list[str]]:
    """Return detected concepts and their auto-derived field names."""
    filters = filters or {}
    detected: list[str] = []

    # Basic keyword detection from text/target/filter hints.
    if _text_matches(theory_text, ("pace", "possessions")):
        detected.append("pace")
    if _text_matches(theory_text, ("rest", "back-to-back", "b2b")):
        detected.append("rest")
    if _text_matches(theory_text, ("altitude", "elevation")):
        detected.append("altitude")

    # Look at filters for implied concepts (e.g., pace_min/max implies pace).
    if any(k in filters for k in ("pace_min", "pace_max")) and "pace" not in detected:
        detected.append("pace")

    auto_fields: list[str] = []
    for concept in detected:
        auto_fields.extend(CONCEPT_REGISTRY.get(concept, []))

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_fields = []
    for f in auto_fields:
        if f in seen:
            continue
        seen.add(f)
        unique_fields.append(f)

    return {"detected_concepts": detected, "auto_derived_fields": unique_fields}

