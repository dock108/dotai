"""Feature generation utilities for EDA.

Given a set of raw stat keys and context flags (rest days, rolling windows),
produce a list of generated features with formulas and categories that the
frontend can display and the backend can compute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .feature_metadata import FeatureSource, FeatureTiming, get_feature_metadata


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
    timing: FeatureTiming = FeatureTiming.PRE_GAME
    source: FeatureSource = FeatureSource.UNKNOWN
    group: str | None = None


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


def _builtin_features() -> list[GeneratedFeature]:
    """Always-helpful derived flags and gaps that don't depend on user raw list."""
    conf_meta = get_feature_metadata("is_conference_game", "situational")
    pace_game_meta = get_feature_metadata("pace_game", "situational")
    pace_home_meta = get_feature_metadata("pace_home_possessions", "situational")
    pace_away_meta = get_feature_metadata("pace_away_possessions", "situational")
    final_total_meta = get_feature_metadata("final_total_points", "derived")
    total_delta_meta = get_feature_metadata("total_delta", "derived")
    cover_margin_meta = get_feature_metadata("cover_margin", "derived")
    rating_diff_meta = get_feature_metadata("rating_diff", "derived")
    proj_points_diff_meta = get_feature_metadata("proj_points_diff", "derived")
    pm_meta = get_feature_metadata("player_minutes", "situational")
    pmr_meta = get_feature_metadata("player_minutes_rolling", "situational")
    pmd_meta = get_feature_metadata("player_minutes_delta", "situational")
    ml_ie_meta = get_feature_metadata("ml_implied_edge", "derived")
    return [
        GeneratedFeature(
            name="is_conference_game",
            formula="1 if conference game else 0",
            category="situational",
            requires=[],
            timing=conf_meta.timing,
            source=conf_meta.source,
            group=conf_meta.group,
        ),
        GeneratedFeature(
            name="pace_game",
            formula="estimated possessions per game",
            category="situational",
            requires=[],
            timing=pace_game_meta.timing,
            source=pace_game_meta.source,
            group=pace_game_meta.group,
        ),
        GeneratedFeature(
            name="pace_home_possessions",
            formula="estimated home possessions",
            category="situational",
            requires=[],
            timing=pace_home_meta.timing,
            source=pace_home_meta.source,
            group=pace_home_meta.group,
        ),
        GeneratedFeature(
            name="pace_away_possessions",
            formula="estimated away possessions",
            category="situational",
            requires=[],
            timing=pace_away_meta.timing,
            source=pace_away_meta.source,
            group=pace_away_meta.group,
        ),
        GeneratedFeature(
            name="final_total_points",
            formula="home_score + away_score",
            category="derived",
            requires=[],
            timing=final_total_meta.timing,
            source=final_total_meta.source,
            group=final_total_meta.group,
        ),
        GeneratedFeature(
            name="total_delta",
            formula="final_total_points - closing_total",
            category="derived",
            requires=[],
            timing=total_delta_meta.timing,
            source=total_delta_meta.source,
            group=total_delta_meta.group,
        ),
        GeneratedFeature(
            name="cover_margin",
            formula="margin_of_victory - closing_spread_home",
            category="derived",
            requires=[],
            timing=cover_margin_meta.timing,
            source=cover_margin_meta.source,
            group=cover_margin_meta.group,
        ),
        GeneratedFeature(
            name="rating_diff",
            formula="home_rating - away_rating",
            category="derived",
            requires=[],
            timing=rating_diff_meta.timing,
            source=rating_diff_meta.source,
            group=rating_diff_meta.group,
        ),
        GeneratedFeature(
            name="proj_points_diff",
            formula="home_proj_points - away_proj_points",
            category="derived",
            requires=[],
            timing=proj_points_diff_meta.timing,
            source=proj_points_diff_meta.source,
            group=proj_points_diff_meta.group,
        ),
        GeneratedFeature(
            name="player_minutes",
            formula="player minutes (if player filter applied)",
            category="situational",
            requires=[],
            timing=pm_meta.timing,
            source=pm_meta.source,
            group=pm_meta.group,
        ),
        GeneratedFeature(
            name="player_minutes_rolling",
            formula="rolling avg minutes before game (if player filter applied)",
            category="situational",
            requires=[],
            timing=pmr_meta.timing,
            source=pmr_meta.source,
            group=pmr_meta.group,
        ),
        GeneratedFeature(
            name="player_minutes_delta",
            formula="player_minutes - player_minutes_rolling",
            category="situational",
            requires=[],
            timing=pmd_meta.timing,
            source=pmd_meta.source,
            group=pmd_meta.group,
        ),
        GeneratedFeature(
            name="ml_implied_edge",
            formula="implied_prob(home_ml) - implied_prob(away_ml)",
            category="derived",
            requires=[],
            timing=ml_ie_meta.timing,
            source=ml_ie_meta.source,
            group=ml_ie_meta.group,
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
    features.extend(_builtin_features())
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

