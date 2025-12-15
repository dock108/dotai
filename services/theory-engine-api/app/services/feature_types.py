"""Shared types for feature generation and computation.

Keep this module dependency-light to avoid circular imports between feature
catalog modules and the main feature engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .feature_metadata import FeatureSource, FeatureTiming


@dataclass
class GeneratedFeature:
    """A generated feature descriptor.

    Attributes:
        name: Machine-friendly feature name (e.g., "points_diff").
        formula: Human-readable expression (e.g., "home_points - away_points").
        category: Feature group for UI filtering (e.g., "raw", "engineered").
        requires: Raw stats needed to compute this feature.
        default_selected: Whether the UI should initially select this feature.
    """

    name: str
    formula: str
    category: str
    requires: List[str]
    timing: FeatureTiming = FeatureTiming.PRE_GAME
    source: FeatureSource = FeatureSource.UNKNOWN
    group: str | None = None
    default_selected: bool = False


