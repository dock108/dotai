from __future__ import annotations

"""
NCAAB derived features combining team/player/pace inputs.
"""

from typing import Any, Dict

from ..utils import safe_diff, safe_sum


def build_derived_features(
    game_id: int,
    team_features: Dict[str, Any],
    player_features: Dict[str, Any],
    pace_features: Dict[str, Any],
) -> Dict[str, Any]:
    home_rating = team_features.get("home_rating")
    away_rating = team_features.get("away_rating")
    pace_home = pace_features.get("pace_home")
    pace_away = pace_features.get("pace_away")

    return {
        "rating_diff": safe_diff(home_rating, away_rating),
        "pace_diff": safe_diff(pace_home, pace_away),
        "pace_total": safe_sum(pace_home, pace_away),
    }

