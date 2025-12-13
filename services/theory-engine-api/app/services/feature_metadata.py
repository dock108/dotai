from __future__ import annotations

"""
Feature metadata and leakage policy for the EDA & Modeling Lab.

Stage 0.1 requires:
- Every feature tagged with provenance/timing (pre-game vs market vs post-game leakage)
- Post-game features excluded from any "deployable" context (allowed only in diagnostics)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class FeatureTiming(str, Enum):
    PRE_GAME = "pre_game"
    MARKET_DERIVED = "market_derived"
    POST_GAME = "post_game"


class FeatureSource(str, Enum):
    # schedule / metadata known before tip-off
    SCHEDULE = "schedule"
    # historical aggregates computed from games before the current game
    ROLLING_HISTORY = "rolling_history"
    # market data available before tip-off (closing line/odds)
    MARKET = "market"
    # per-game boxscore stats for the same game (leakage if used to predict)
    BOXSCORE = "boxscore"
    # final results or metrics derived from final results (leakage)
    RESULT = "result"
    # projections / ratings (assumed pre-game; depends on upstream feed)
    PROJECTION = "projection"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FeatureMetadata:
    timing: FeatureTiming
    source: FeatureSource
    description: str | None = None
    group: str | None = None

    @property
    def diagnostic_only(self) -> bool:
        return self.timing == FeatureTiming.POST_GAME


# Explicit overrides for known feature names.
_OVERRIDES: Dict[str, FeatureMetadata] = {
    # Market (pre-game) signals
    "closing_ml_home": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "closing_ml_away": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "closing_spread_home": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "closing_spread_home_price": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "closing_spread_away": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "closing_spread_away_price": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "closing_total": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "closing_total_price": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "ml_edge_home": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    "spread_edge_home": FeatureMetadata(FeatureTiming.MARKET_DERIVED, FeatureSource.MARKET, group="Market context"),
    # Pre-game schedule/context
    "is_conference_game": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.SCHEDULE, group="Discipline"),
    "home_rest_days": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.SCHEDULE, group="Discipline"),
    "away_rest_days": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.SCHEDULE, group="Discipline"),
    "rest_advantage": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.SCHEDULE, group="Discipline"),
    # Rolling history (pre-game)
    "player_minutes_rolling": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.ROLLING_HISTORY, group="Discipline"),
    # Projections/ratings (assumed pre-game)
    "home_rating": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.PROJECTION, group="Efficiency"),
    "away_rating": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.PROJECTION, group="Efficiency"),
    "rating_diff": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.PROJECTION, group="Efficiency"),
    "home_proj_points": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.PROJECTION, group="Scoring"),
    "away_proj_points": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.PROJECTION, group="Scoring"),
    "proj_points_diff": FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.PROJECTION, group="Scoring"),
    # Explicit post-game / result-derived leakage
    "home_score": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Scoring"),
    "away_score": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Scoring"),
    "winner": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Scoring"),
    "did_home_cover": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Market context"),
    "did_away_cover": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Market context"),
    "total_result": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Scoring"),
    "margin_of_victory": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Scoring"),
    "combined_score": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Scoring"),
    "final_total_points": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Scoring"),
    "total_delta": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Market context"),
    "cover_margin": FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.RESULT, group="Market context"),
}


def get_feature_metadata(name: str, category: Optional[str] = None) -> FeatureMetadata:
    """
    Best-effort classification:
    - rolling_* => pre-game (derived from prior games)
    - home_/away_/total_ and *_diff (non-rolling) => boxscore (post-game leakage)
    - pace_* computed from same-game boxscore => leakage by default
    - unknown => conservative UNKNOWN (treated as deployable unless explicitly post_game)
    """
    if name in _OVERRIDES:
        return _OVERRIDES[name]

    if name.startswith("rolling_"):
        return FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.ROLLING_HISTORY, group=_infer_group(name))

    if name.startswith("pace_"):
        # In this codebase pace_* is currently computed from the same game's boxscore.
        return FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.BOXSCORE, group="Pace")

    # Boxscore-based generated features (same-game stats)
    if name.startswith(("home_", "away_", "total_")) or name.endswith("_diff"):
        # Unless it's a rolling_* feature, these are computed from the same game's boxscore row.
        return FeatureMetadata(FeatureTiming.POST_GAME, FeatureSource.BOXSCORE, group=_infer_group(name))

    # Fallback: for new/unknown features we don't want to accidentally block progress.
    # They can be upgraded to explicit overrides as we harden the pipeline.
    return FeatureMetadata(FeatureTiming.PRE_GAME, FeatureSource.UNKNOWN, group=_infer_group(name))


def _infer_group(name: str) -> str:
    """Heuristic grouping for Stage 1.1 (structure first, math later)."""
    n = name.lower()
    if any(k in n for k in ("pace", "possessions")):
        return "Pace"
    if any(k in n for k in ("reb", "oreb", "dreb", "orb", "drb")):
        return "Rebounding"
    if any(k in n for k in ("ast", "assist")):
        return "Efficiency"
    if any(k in n for k in ("fg", "efg", "ts", "pct", "3p", "ft")):
        return "Efficiency"
    if any(k in n for k in ("tov", "turnover", "foul", "pf")):
        return "Discipline"
    if any(k in n for k in ("pts", "points", "score", "margin", "total")):
        return "Scoring"
    if any(k in n for k in ("closing_", "line", "odds", "implied", "edge")):
        return "Market context"
    return "Other"


