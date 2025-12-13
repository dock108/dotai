from __future__ import annotations

from typing import Any, List, Tuple

from ..feature_metadata import FeatureTiming, get_feature_metadata


def feature_policy_report(features: List[Any], context: str) -> Tuple[List[Any], dict[str, Any]]:
    """Filter requested features by leakage policy and return a report."""
    allowed: List[Any] = []
    dropped_post_game: List[str] = []
    for f in features:
        meta = get_feature_metadata(getattr(f, "name", ""), getattr(f, "category", None))
        if not getattr(f, "timing", None):
            f.timing = meta.timing.value
        if not getattr(f, "source", None):
            f.source = meta.source.value
        if not getattr(f, "group", None):
            f.group = meta.group
        if context == "deployable" and meta.timing == FeatureTiming.POST_GAME:
            dropped_post_game.append(getattr(f, "name", ""))
            continue
        allowed.append(f)
    return allowed, {
        "context": context,
        "dropped_post_game_features": dropped_post_game,
        "dropped_post_game_count": len(dropped_post_game),
        "contains_post_game_features": len(dropped_post_game) > 0,
    }


