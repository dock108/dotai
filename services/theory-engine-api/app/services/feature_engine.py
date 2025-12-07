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


def _builtin_features() -> list[GeneratedFeature]:
    """Always-helpful derived flags and gaps that don't depend on user raw list."""
    return [
        GeneratedFeature(
            name="is_conference_game",
            formula="1 if conference game else 0",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="pace_game",
            formula="estimated possessions per game",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="pace_home_possessions",
            formula="estimated home possessions",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="pace_away_possessions",
            formula="estimated away possessions",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="final_total_points",
            formula="home_score + away_score",
            category="derived",
            requires=[],
        ),
        GeneratedFeature(
            name="total_delta",
            formula="final_total_points - closing_total",
            category="derived",
            requires=[],
        ),
        GeneratedFeature(
            name="cover_margin",
            formula="margin_of_victory - closing_spread_home",
            category="derived",
            requires=[],
        ),
        GeneratedFeature(
            name="rating_diff",
            formula="home_rating - away_rating",
            category="derived",
            requires=[],
        ),
        GeneratedFeature(
            name="proj_points_diff",
            formula="home_proj_points - away_proj_points",
            category="derived",
            requires=[],
        ),
        GeneratedFeature(
            name="player_minutes",
            formula="player minutes (if player filter applied)",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="player_minutes_rolling",
            formula="rolling avg minutes before game (if player filter applied)",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="player_minutes_delta",
            formula="player_minutes - player_minutes_rolling",
            category="situational",
            requires=[],
        ),
        GeneratedFeature(
            name="ml_implied_edge",
            formula="implied_prob(home_ml) - implied_prob(away_ml)",
            category="derived",
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

