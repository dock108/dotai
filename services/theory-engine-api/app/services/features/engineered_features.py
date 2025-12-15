"""Engineered (non-raw) features that are available but should not be auto-selected.

These are cross-cutting features like pace, conference flags, player minutes, and
market-derived diagnostics. They should be available as options, but the UI should
decide selection explicitly.
"""

from __future__ import annotations

from ..feature_types import GeneratedFeature
from ..feature_metadata import get_feature_metadata


def engineered_feature_catalog() -> list[GeneratedFeature]:
    # NOTE: default_selected=False for all engineered features.
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
            category="engineered",
            requires=[],
            timing=conf_meta.timing,
            source=conf_meta.source,
            group=conf_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="pace_game",
            formula="estimated possessions per game",
            category="engineered",
            requires=[],
            timing=pace_game_meta.timing,
            source=pace_game_meta.source,
            group=pace_game_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="pace_home_possessions",
            formula="estimated home possessions",
            category="engineered",
            requires=[],
            timing=pace_home_meta.timing,
            source=pace_home_meta.source,
            group=pace_home_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="pace_away_possessions",
            formula="estimated away possessions",
            category="engineered",
            requires=[],
            timing=pace_away_meta.timing,
            source=pace_away_meta.source,
            group=pace_away_meta.group,
            default_selected=False,
        ),
        # Diagnostic/post-game engineered features (available, but never auto-selected)
        GeneratedFeature(
            name="final_total_points",
            formula="home_score + away_score",
            category="engineered",
            requires=[],
            timing=final_total_meta.timing,
            source=final_total_meta.source,
            group=final_total_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="total_delta",
            formula="final_total_points - closing_total",
            category="engineered",
            requires=[],
            timing=total_delta_meta.timing,
            source=total_delta_meta.source,
            group=total_delta_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="cover_margin",
            formula="margin_of_victory - closing_spread_home",
            category="engineered",
            requires=[],
            timing=cover_margin_meta.timing,
            source=cover_margin_meta.source,
            group=cover_margin_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="rating_diff",
            formula="home_rating - away_rating",
            category="engineered",
            requires=[],
            timing=rating_diff_meta.timing,
            source=rating_diff_meta.source,
            group=rating_diff_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="proj_points_diff",
            formula="home_proj_points - away_proj_points",
            category="engineered",
            requires=[],
            timing=proj_points_diff_meta.timing,
            source=proj_points_diff_meta.source,
            group=proj_points_diff_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="player_minutes",
            formula="player minutes (if player filter applied)",
            category="engineered",
            requires=[],
            timing=pm_meta.timing,
            source=pm_meta.source,
            group=pm_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="player_minutes_rolling",
            formula="rolling avg minutes before game (if player filter applied)",
            category="engineered",
            requires=[],
            timing=pmr_meta.timing,
            source=pmr_meta.source,
            group=pmr_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="player_minutes_delta",
            formula="player_minutes - player_minutes_rolling",
            category="engineered",
            requires=[],
            timing=pmd_meta.timing,
            source=pmd_meta.source,
            group=pmd_meta.group,
            default_selected=False,
        ),
        GeneratedFeature(
            name="ml_implied_edge",
            formula="implied_prob(home_ml) - implied_prob(away_ml)",
            category="engineered",
            requires=[],
            timing=ml_ie_meta.timing,
            source=ml_ie_meta.source,
            group=ml_ie_meta.group,
            default_selected=False,
        ),
    ]


