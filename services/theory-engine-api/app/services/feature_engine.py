"""Feature generation utilities for EDA.

Given a set of raw stat keys and context flags (rest days, rolling windows),
produce a list of generated features with formulas and categories that the
frontend can display and the backend can compute.
"""

from __future__ import annotations

from .feature_metadata import get_feature_metadata
from .feature_types import GeneratedFeature
from .features.engineered_features import engineered_feature_catalog


def _raw_features(raw_stats: list[str]) -> list[GeneratedFeature]:
    features: list[GeneratedFeature] = []
    for stat in raw_stats:
        home_meta = get_feature_metadata(f"home_{stat}", "raw")
        features.append(
            GeneratedFeature(
                name=f"home_{stat}",
                formula=f"home {stat}",
                category="raw",
                requires=[stat],
                timing=home_meta.timing,
                source=home_meta.source,
                group=home_meta.group,
            )
        )
        away_meta = get_feature_metadata(f"away_{stat}", "raw")
        features.append(
            GeneratedFeature(
                name=f"away_{stat}",
                formula=f"away {stat}",
                category="raw",
                requires=[stat],
                timing=away_meta.timing,
                source=away_meta.source,
                group=away_meta.group,
            )
        )
    return features


def _differential_features(raw_stats: list[str]) -> list[GeneratedFeature]:
    features: list[GeneratedFeature] = []
    for stat in raw_stats:
        meta = get_feature_metadata(f"{stat}_diff", "differential")
        features.append(
            GeneratedFeature(
                name=f"{stat}_diff",
                formula=f"home_{stat} - away_{stat}",
                category="differential",
                requires=[stat],
                timing=meta.timing,
                source=meta.source,
                group=meta.group,
            )
        )
    return features


def _combined_features(raw_stats: list[str]) -> list[GeneratedFeature]:
    features: list[GeneratedFeature] = []
    for stat in raw_stats:
        meta = get_feature_metadata(f"total_{stat}", "combined")
        features.append(
            GeneratedFeature(
                name=f"total_{stat}",
                formula=f"home_{stat} + away_{stat}",
                category="combined",
                requires=[stat],
                timing=meta.timing,
                source=meta.source,
                group=meta.group,
            )
        )
    return features


def _situational_features(include_rest_days: bool) -> list[GeneratedFeature]:
    if not include_rest_days:
        return []
    home_meta = get_feature_metadata("home_rest_days", "situational")
    away_meta = get_feature_metadata("away_rest_days", "situational")
    rest_meta = get_feature_metadata("rest_advantage", "situational")
    return [
        GeneratedFeature(
            name="home_rest_days",
            formula="days since home team's last game",
            category="situational",
            requires=[],
            timing=home_meta.timing,
            source=home_meta.source,
            group=home_meta.group,
        ),
        GeneratedFeature(
            name="away_rest_days",
            formula="days since away team's last game",
            category="situational",
            requires=[],
            timing=away_meta.timing,
            source=away_meta.source,
            group=away_meta.group,
        ),
        GeneratedFeature(
            name="rest_advantage",
            formula="home_rest_days - away_rest_days",
            category="situational",
            requires=[],
            timing=rest_meta.timing,
            source=rest_meta.source,
            group=rest_meta.group,
        ),
    ]


def _rolling_features(raw_stats: list[str], window: int) -> list[GeneratedFeature]:
    features: list[GeneratedFeature] = []
    for stat in raw_stats:
        h_meta = get_feature_metadata(f"rolling_{stat}_{window}_home", "rolling")
        features.append(
            GeneratedFeature(
                name=f"rolling_{stat}_{window}_home",
                formula=f"avg home_{stat} over last {window} games",
                category="rolling",
                requires=[stat],
                timing=h_meta.timing,
                source=h_meta.source,
                group=h_meta.group,
            )
        )
        a_meta = get_feature_metadata(f"rolling_{stat}_{window}_away", "rolling")
        features.append(
            GeneratedFeature(
                name=f"rolling_{stat}_{window}_away",
                formula=f"avg away_{stat} over last {window} games",
                category="rolling",
                requires=[stat],
                timing=a_meta.timing,
                source=a_meta.source,
                group=a_meta.group,
            )
        )
        d_meta = get_feature_metadata(f"rolling_{stat}_{window}_diff", "rolling")
        features.append(
            GeneratedFeature(
                name=f"rolling_{stat}_{window}_diff",
                formula=f"rolling_{stat}_{window}_home - rolling_{stat}_{window}_away",
                category="rolling",
                requires=[stat],
                timing=d_meta.timing,
                source=d_meta.source,
                group=d_meta.group,
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
    # Engineered features are available but should not be auto-selected.
    features.extend(engineered_feature_catalog())
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

