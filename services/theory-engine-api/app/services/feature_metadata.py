"""Metadata definitions for generated features (timing, source, grouping).

This keeps feature policy decisions (e.g., leakage enforcement) centralized.
If a feature is not explicitly mapped, we return a conservative default that
assumes it is a pre-game stat-driven feature.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FeatureTiming(Enum):
    """When the feature is available relative to game start."""

    PRE_GAME = "pre_game"
    MARKET_DERIVED = "market_derived"
    POST_GAME = "post_game"  # diagnostic-only; should be excluded from deployable contexts


class FeatureSource(Enum):
    """Where the feature originates."""

    UNKNOWN = "unknown"
    STATS = "stats"
    MARKET = "market"
    DERIVED = "derived"


@dataclass
class FeatureMetadata:
    timing: FeatureTiming = FeatureTiming.PRE_GAME
    source: FeatureSource = FeatureSource.UNKNOWN
    group: Optional[str] = None


# Explicit per-feature overrides.
_FEATURE_MAP: dict[str, FeatureMetadata] = {
    # Situational / availability
    "home_rest_days": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.STATS, "situational"),
    "away_rest_days": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.STATS, "situational"),
    "rest_advantage": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.DERIVED, "situational"),
}


def _infer_group(name: str) -> Optional[str]:
    """Lightweight grouping heuristic for display; non-authoritative."""
    lowered = name.lower()
    if any(key in lowered for key in ["fg", "efg", "ts", "shoot", "3pt", "ft"]):
        return "efficiency"
    if any(key in lowered for key in ["rebound", "orb", "drb"]):
        return "rebounding"
    if any(key in lowered for key in ["assist", "turnover", "ast"]):
        return "discipline"
    if "pace" in lowered or "poss" in lowered:
        return "pace"
    return None


def get_feature_metadata(name: str, category: Optional[str] = None) -> FeatureMetadata:
    """Return metadata for a feature; falls back to conservative defaults."""
    if name in _FEATURE_MAP:
        return _FEATURE_MAP[name]

    # Heuristics: rolling / post-game detection
    lowered = name.lower()
    timing = FeatureTiming.POST_GAME if lowered.startswith("final_") else FeatureTiming.PRE_GAME
    source = FeatureSource.STATS

    # Market-derived signals
    if any(key in lowered for key in ["closing_", "live_", "odds", "spread", "total", "moneyline", "line"]):
        source = FeatureSource.MARKET
        # market lines are only known pre-game; outcomes are post-game
        if any(key in lowered for key in ["did_", "result", "winner"]):
            timing = FeatureTiming.POST_GAME
        else:
            timing = FeatureTiming.MARKET_DERIVED

    group = _infer_group(name)
    return FeatureMetadata(timing=timing, source=source, group=group)
