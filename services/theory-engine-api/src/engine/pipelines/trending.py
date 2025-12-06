from __future__ import annotations

from typing import Any, Dict, Iterable, List

from engine.common.result_schema import TrendingIndicator
from engine.common.micro_model import MicroModel
from engine.common.feature_builder import FeatureBuilder
from .interfaces import OddsHistoryProvider, PipelineContext
from engine.common.utils import expected_value


class TrendingPipeline:
    """
    Monitor odds movement and distance-to-positive-EV.
    """

    def __init__(self, history_provider: OddsHistoryProvider, micro_model: MicroModel, feature_builder: FeatureBuilder):
        self.history_provider = history_provider
        self.micro_model = micro_model
        self.feature_builder = feature_builder

    async def run(self, ctx: PipelineContext) -> List[TrendingIndicator]:
        rows = await self.history_provider.odds_history(ctx.league_id)
        indicators: List[TrendingIndicator] = []
        for row in rows:
            features = self.feature_builder.build(row)
            ev_now = self.micro_model.compute_ev(row, features)
            implied_prob = row.get("implied_prob")
            true_prob = features.get("true_prob") if isinstance(features, dict) else None
            ev_est = expected_value(true_prob, row.get("odds"), odds_format="american") if true_prob is not None else ev_now

            strength = ev_est if ev_est is not None else 0.0
            direction = "up" if strength and strength > 0 else "down" if strength and strength < 0 else "neutral"
            indicators.append(
                TrendingIndicator(
                    event_id=row.get("game_id"),
                    market=self.micro_model.__class__.__name__,
                    odds=row.get("odds"),
                    implied_prob=implied_prob,
                    ev=ev_now,
                    features=features,
                    timestamp=row.get("ts") or row.get("game_date"),
                    trend_strength=abs(strength),
                    trend_direction=direction,
                )
            )
        return indicators

