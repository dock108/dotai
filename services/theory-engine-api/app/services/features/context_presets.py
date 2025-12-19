"""Context preset definitions.

These define what features are included for each preset level.
Presets are authoritative - if a feature isn't reachable through a preset, it can't be added.
"""

from __future__ import annotations

from typing import TypedDict


class ContextFeatureSet(TypedDict):
    """Feature set by semantic group."""

    game: list[str]
    market: list[str]
    team: list[str]
    player: list[str]
    diagnostic: list[str]


# -----------------------------------------------------------------------------
# Preset Definitions
# -----------------------------------------------------------------------------

# IMPORTANT: "minimal" must be truly empty - no pace, no conference, nothing.
# Only user-selected base stats are used when preset is "minimal".
PRESET_MINIMAL: ContextFeatureSet = {
    # EMPTY - only base stats derived features are used
    "game": [],
    "market": [],
    "team": [],
    "player": [],
    "diagnostic": [],
}

# Standard adds conference game only - NO pace (pace is in verbose)
PRESET_STANDARD: ContextFeatureSet = {
    "game": ["is_conference_game"],
    "market": [],
    "team": [],
    "player": [],
    "diagnostic": [],
}

# Market-aware adds closing lines
PRESET_MARKET_AWARE: ContextFeatureSet = {
    "game": ["is_conference_game"],
    "market": ["closing_spread_home", "closing_total"],
    "team": [],
    "player": [],
    "diagnostic": [],
}

# Player-aware adds rest and player data
PRESET_PLAYER_AWARE: ContextFeatureSet = {
    "game": ["is_conference_game", "home_rest_days", "away_rest_days"],
    "market": [],
    "team": [],
    "player": ["player_minutes", "player_minutes_rolling"],
    "diagnostic": [],
}

# Verbose includes everything
PRESET_VERBOSE: ContextFeatureSet = {
    "game": [
        "is_conference_game",
        "pace_game",
        "home_rest_days",
        "away_rest_days",
        "rest_advantage",
    ],
    "market": ["closing_spread_home", "closing_total", "ml_implied_edge"],
    "team": ["rating_diff", "proj_points_diff"],
    "player": ["player_minutes", "player_minutes_rolling", "player_minutes_delta"],
    "diagnostic": [],
}

# Mapping of preset names to their definitions
CONTEXT_PRESETS: dict[str, ContextFeatureSet] = {
    "minimal": PRESET_MINIMAL,
    "standard": PRESET_STANDARD,
    "market_aware": PRESET_MARKET_AWARE,
    "player_aware": PRESET_PLAYER_AWARE,
    "verbose": PRESET_VERBOSE,
    "custom": PRESET_MINIMAL,  # custom starts empty
}


# -----------------------------------------------------------------------------
# Feature Group Metadata
# -----------------------------------------------------------------------------

GAME_CONTEXT_FEATURES = {
    "is_conference_game": "1 if conference game else 0",
    "pace_game": "estimated possessions per game",
    "pace_home_possessions": "estimated home possessions",
    "pace_away_possessions": "estimated away possessions",
    "home_rest_days": "days since home team's last game",
    "away_rest_days": "days since away team's last game",
    "rest_advantage": "home_rest_days - away_rest_days",
}

MARKET_CONTEXT_FEATURES = {
    "closing_spread_home": "closing spread for home team",
    "closing_total": "closing over/under line",
    "ml_implied_edge": "moneyline implied probability difference",
}

TEAM_STRENGTH_FEATURES = {
    "rating_diff": "home_rating - away_rating",
    "proj_points_diff": "home_proj_points - away_proj_points",
}

PLAYER_CONTEXT_FEATURES = {
    "player_minutes": "player minutes (if player filter applied)",
    "player_minutes_rolling": "rolling avg minutes before game",
    "player_minutes_delta": "player_minutes - player_minutes_rolling",
}

# Diagnostic features (post-game, leaky)
DIAGNOSTIC_FEATURES = {
    "final_total_points": "home_score + away_score",
    "total_delta": "final_total_points - closing_total",
    "cover_margin": "margin_of_victory - closing_spread_home",
}


def get_preset_features(preset: str) -> ContextFeatureSet:
    """Get the feature set for a preset name."""
    return CONTEXT_PRESETS.get(preset, PRESET_MINIMAL)


def expand_context_features(context_features: ContextFeatureSet) -> list[str]:
    """Flatten all context features into a single list."""
    features: list[str] = []
    for group in ["game", "market", "team", "player", "diagnostic"]:
        features.extend(context_features.get(group, []))
    return features


def is_diagnostic_feature(name: str) -> bool:
    """Check if a feature is diagnostic (post-game leaky)."""
    return name in DIAGNOSTIC_FEATURES

