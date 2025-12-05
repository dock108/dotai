"""Feature generation utilities for EDA.

Given a set of raw stat keys and context flags (rest days, rolling windows),
produce a list of generated features with formulas and categories that the
frontend can display and the backend can compute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class GeneratedFeature:
    """A generated feature descriptor.

    Attributes:
        name: Machine-friendly feature name (e.g., "points_diff").
        formula: Human-readable expression (e.g., "home_points - away_points").
        category: One of ["raw", "differential", "combined", "situational", "rolling"].
        requires: Raw stats needed to compute this feature.
    """

    name: str
    formula: str
    category: str
    requires: List[str]


def _raw_features(raw_stats: list[str]) -> list[GeneratedFeature]:
    features: list[GeneratedFeature] = []
    for stat in raw_stats:
        features.append(
            GeneratedFeature(
                name=f"home_{stat}",
                formula=f"home {stat}",
                category="raw",
                requires=[stat],
            )
        )
        features.append(
            GeneratedFeature(
                name=f"away_{stat}",
                formula=f"away {stat}",
                category="raw",
                requires=[stat],
            )
        )
    return features


def _differential_features(raw_stats: list[str]) -> list[GeneratedFeature]:
    features: list[GeneratedFeature] = []
    for stat in raw_stats:
        features.append(
            GeneratedFeature(
                name=f"{stat}_diff",
                formula=f"home_{stat} - away_{stat}",
                category="differential",
                requires=[stat],
            )
        )
    return features


def _combined_features(raw_stats: list[str]) -> list[GeneratedFeature]:
    features: list[GeneratedFeature] = []
    for stat in raw_stats:
        features.append(
            GeneratedFeature(
                name=f"total_{stat}",
                formula=f"home_{stat} + away_{stat}",
                category="combined",
                requires=[stat],
            )
        )
    return features


def _situational_features(include_rest_days: bool) -> list[GeneratedFeature]:
    if not include_rest_days:
        return []
    return [
        GeneratedFeature(
            name="home_rest_days",
            formula="days since home team's last game",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="away_rest_days",
            formula="days since away team's last game",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="rest_advantage",
            formula="home_rest_days - away_rest_days",
            category="situational",
            requires=[],
        ),
    ]


def _rolling_features(raw_stats: list[str], window: int) -> list[GeneratedFeature]:
    features: list[GeneratedFeature] = []
    for stat in raw_stats:
        features.append(
            GeneratedFeature(
                name=f"rolling_{stat}_{window}_home",
                formula=f"avg home_{stat} over last {window} games",
                category="rolling",
                requires=[stat],
            )
        )
        features.append(
            GeneratedFeature(
                name=f"rolling_{stat}_{window}_away",
                formula=f"avg away_{stat} over last {window} games",
                category="rolling",
                requires=[stat],
            )
        )
        features.append(
            GeneratedFeature(
                name=f"rolling_{stat}_{window}_diff",
                formula=f"rolling_{stat}_{window}_home - rolling_{stat}_{window}_away",
                category="rolling",
                requires=[stat],
            )
        )
    return features


def generate_features(
    raw_stats: list[str],
    include_rest_days: bool,
    include_rolling: bool,
    rolling_window: int = 5,
) -> list[GeneratedFeature]:
    """Generate feature descriptors from selected raw stats and context flags."""
    # Deduplicate and preserve input order
    seen: set[str] = set()
    deduped_stats = []
    for stat in raw_stats:
        if stat not in seen:
            seen.add(stat)
            deduped_stats.append(stat)

    features: list[GeneratedFeature] = []
    features.extend(_raw_features(deduped_stats))
    features.extend(_differential_features(deduped_stats))
    features.extend(_combined_features(deduped_stats))
    features.extend(_situational_features(include_rest_days))
    if include_rolling:
        features.extend(_rolling_features(deduped_stats, rolling_window))

    return features


def summarize_features(features: list[GeneratedFeature], raw_stats: list[str], include_rest_days: bool) -> str:
    """Return a short human summary for the frontend."""
    rest_part = " + rest days" if include_rest_days else ""
    return f"{len(features)} features generated from {len(set(raw_stats))} stats{rest_part}"

