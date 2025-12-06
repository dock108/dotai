from __future__ import annotations

"""
Layered feature builders.

Levels:
- Level 0 (required): closing odds/lines, final score, basic metadata.
- Level 1 (domain): ratings, projections, pace if available.
- Level 2 (derived): deltas, rolling/z-scores/volatility, implied vs actual gaps.

CombinedFeatureBuilder merges the outputs from the configured builders while
gracefully tolerating missing data (skips on exception or None values).
"""

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .feature_builder import FeatureBuilder
from .utils import implied_probability, merge_features


def _safe_diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a - b


def _safe_ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _safe_zscore(val: float | None, series: Sequence[float | None]) -> float | None:
    clean = [x for x in series if x is not None]
    if val is None or len(clean) < 2:
        return None
    mu = mean(clean)
    sigma = pstdev(clean)
    if sigma == 0:
        return None
    return (val - mu) / sigma


def _safe_volatility(series: Sequence[float | None]) -> float | None:
    clean = [x for x in series if x is not None]
    if len(clean) < 2:
        return None
    return pstdev(clean)


def _extract(
    mapping: Mapping[str, Any] | None, keys: Iterable[str]
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not mapping:
        return out
    for key in keys:
        if key in mapping and mapping[key] is not None:
            out[key] = mapping[key]
    return out


@dataclass
class Level0RequiredBuilder(FeatureBuilder):
    """
    Required features (always available): closing odds/lines, score, metadata.
    """

    mode: str = "minimal"

    def __post_init__(self):
        super().__init__(mode=self.mode)

    def required_fields(self) -> Iterable[str]:
        return [
            "closing",
            "lines",
            "result",
            "metadata",
        ]

    def build_minimal(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        closing = event.get("closing", {})
        lines = event.get("lines", {})
        result = event.get("result", {})
        meta = event.get("metadata", {})

        payload: Dict[str, Any] = {}
        payload.update(_extract(closing, ["closing_ml_home", "closing_ml_away"]))
        payload.update(
            _extract(lines, ["closing_spread_home", "closing_spread_home_price", "closing_total", "closing_total_price"])
        )
        payload.update(
            _extract(
                result,
                [
                    "home_score",
                    "away_score",
                    "winner",
                    "did_home_cover",
                    "did_away_cover",
                    "total_result",
                    "margin_of_victory",
                    "combined_score",
                ],
            )
        )
        payload.update(_extract(meta, ["season", "league_id", "game_id", "game_date", "home_team", "away_team"]))
        return payload

    def build_full(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        # For Level 0, full == minimal
        return self.build_minimal(event)


@dataclass
class Level1DomainBuilder(FeatureBuilder):
    """
    Domain-level features (team ratings, projections, pace).
    """

    mode: str = "minimal"

    def __post_init__(self):
        super().__init__(mode=self.mode)

    def required_fields(self) -> Iterable[str]:
        return ["ratings", "projections", "pace"]

    def build_minimal(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        ratings = event.get("ratings", {}) or {}
        projections = event.get("projections", {}) or {}
        pace = event.get("pace", {}) or {}

        payload: Dict[str, Any] = {}
        payload.update(
            _extract(
                ratings,
                [
                    "home_rating",
                    "away_rating",
                ],
            )
        )
        payload.update(
            _extract(
                projections,
                [
                    "home_proj_points",
                    "away_proj_points",
                ],
            )
        )
        payload.update(_extract(pace, ["pace_home", "pace_away"]))
        return payload

    def build_full(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        # Full mode can include any extended projections/ratings present
        ratings = event.get("ratings", {}) or {}
        projections = event.get("projections", {}) or {}
        pace = event.get("pace", {}) or {}

        payload = self.build_minimal(event)
        payload.update(_extract(ratings, ["home_rating_trend", "away_rating_trend"]))
        payload.update(
            _extract(
                projections,
                [
                    "home_proj_reb",
                    "away_proj_reb",
                    "home_proj_ast",
                    "away_proj_ast",
                ],
            )
        )
        payload.update(_extract(pace, ["pace_proj_home", "pace_proj_away"]))
        return payload


@dataclass
class Level2DerivedBuilder(FeatureBuilder):
    """
    Derived features (deltas, rolling, z-scores, volatility, implied gaps).
    """

    mode: str = "minimal"

    def __post_init__(self):
        super().__init__(mode=self.mode)

    def required_fields(self) -> Iterable[str]:
        return [
            "closing",
            "lines",
            "result",
            "ratings",
            "projections",
            "pace",
            "history",
        ]

    def build_minimal(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        closing = event.get("closing", {}) or {}
        lines = event.get("lines", {}) or {}
        result = event.get("result", {}) or {}
        ratings = event.get("ratings", {}) or {}
        projections = event.get("projections", {}) or {}
        pace = event.get("pace", {}) or {}

        payload: Dict[str, Any] = {}
        payload["ml_edge_home"] = _safe_diff(
            implied_probability(closing.get("closing_ml_home"), "american"),
            implied_probability(closing.get("closing_ml_away"), "american"),
        )
        payload["spread_edge_home"] = _safe_diff(lines.get("closing_spread_home"), 0.0)
        payload["total_gap"] = _safe_diff(result.get("combined_score"), lines.get("closing_total"))

        payload["rating_diff"] = _safe_diff(ratings.get("home_rating"), ratings.get("away_rating"))
        payload["proj_points_diff"] = _safe_diff(projections.get("home_proj_points"), projections.get("away_proj_points"))
        payload["pace_diff"] = _safe_diff(pace.get("pace_home"), pace.get("pace_away"))

        return {k: v for k, v in payload.items() if v is not None}

    def build_full(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        base = self.build_minimal(event)
        history = event.get("history", {}) or {}

        # Rolling averages and z-scores if supplied
        for key, series in history.items():
            if not isinstance(series, Sequence):
                continue
            base[f"{key}_volatility"] = _safe_volatility(series)
            latest = series[-1] if series else None
            base[f"{key}_zscore"] = _safe_zscore(latest, series)

        # Implied vs actual probability gaps (if true_prob provided)
        closing = event.get("closing", {}) or {}
        true_prob = event.get("true_prob", {}) or {}
        for side in ("home", "away"):
            ml_key = f"closing_ml_{side}"
            prob_key = f"{side}_true_prob"
            gap_key = f"{side}_prob_gap"
            ml_prob = implied_probability(closing.get(ml_key), "american")
            gap = _safe_diff(true_prob.get(prob_key), ml_prob)
            if gap is not None:
                base[gap_key] = gap

        # Spread/total outcomes scaled by lines if present
        lines = event.get("lines", {}) or {}
        result = event.get("result", {}) or {}
        base["cover_margin"] = _safe_diff(result.get("margin_of_victory"), lines.get("closing_spread_home"))
        base["total_delta"] = _safe_diff(result.get("combined_score"), lines.get("closing_total"))

        # Normalize some ratios when possible
        base["rating_ratio"] = _safe_ratio(
            event.get("ratings", {}).get("home_rating"),
            event.get("ratings", {}).get("away_rating"),
        )

        return {k: v for k, v in base.items() if v is not None}


class CombinedFeatureBuilder(FeatureBuilder):
    """
    Composite builder that merges outputs from child builders.
    Exceptions inside children are swallowed to keep admin-mode fast.
    """

    def __init__(self, builders: List[FeatureBuilder], mode: str = "minimal"):
        super().__init__(mode=mode)
        self.builders = builders

    def required_fields(self) -> Iterable[str]:
        fields: list[str] = []
        for b in self.builders:
            try:
                fields.extend(list(b.required_fields()))
            except Exception:
                continue
        return fields

    def build_minimal(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        output: Dict[str, Any] = {}
        for builder in self.builders:
            try:
                output = merge_features(output, builder.build_minimal(event))
            except Exception:
                continue
        return output

    def build_full(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        output: Dict[str, Any] = {}
        for builder in self.builders:
            try:
                output = merge_features(output, builder.build_full(event))
            except Exception:
                continue
        return output


def build_combined_feature_builder(mode: str = "admin") -> CombinedFeatureBuilder:
    """
    Factory for Admin vs Full CombinedFeatureBuilder configurations.

    Admin mode: Level 0 only (fast validation).
    Full mode: Level 0 + Level 1 + Level 2.
    """
    normalized = (mode or "admin").lower()
    level0 = Level0RequiredBuilder(mode="minimal" if normalized == "admin" else "full")
    if normalized == "admin":
        return CombinedFeatureBuilder([level0], mode="minimal")

    level1 = Level1DomainBuilder(mode="full")
    level2 = Level2DerivedBuilder(mode="full")
    return CombinedFeatureBuilder([level0, level1, level2], mode="full")

