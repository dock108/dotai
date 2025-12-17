"""Layer definitions for measurement, concepts, and explanatory features."""

from __future__ import annotations

# Measurement fields: always-on metrics derived directly from game results and odds.
MEASUREMENT_FIELDS: set[str] = {
    "home_score",
    "away_score",
    "combined_score",
    "margin_of_victory",
    "closing_spread_home",
    "closing_total",
    "did_home_cover",
    "total_result",
    "winner",
    "closing_ml_home",
    "closing_ml_away",
}

# Concept registry: minimal derived fields computed only when the concept is referenced.
CONCEPT_REGISTRY: dict[str, list[str]] = {
    "pace": ["pace_game", "pace_home_possessions", "pace_away_possessions"],
    "rest": ["home_rest_days", "away_rest_days", "rest_advantage"],
    # Placeholder for future concepts; add as needed.
    "altitude": ["altitude_ft", "altitude_delta"],
}

# Explanatory features remain in engineered_feature_catalog(); kept here for clarity.
EXPLANATORY_GROUP_LABEL = "explanatory"

