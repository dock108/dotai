from __future__ import annotations

from typing import Any, Dict, Iterable, List

from engine.common.micro_model import MicroModel
from engine.common.result_schema import LiveSignal
from engine.common.feature_builder import FeatureBuilder
from .interfaces import LiveOddsProvider, PipelineContext


class LivePipeline:
    """
    Live opportunities and next-to-trigger signals.
    """

    def __init__(self, odds_provider: LiveOddsProvider, micro_model: MicroModel, feature_builder: FeatureBuilder):
        self.odds_provider = odds_provider
        self.micro_model = micro_model
        self.feature_builder = feature_builder

    async def run(self, ctx: PipelineContext) -> List[LiveSignal]:
        odds_rows = await self.odds_provider.current_odds(ctx.league_id)
        signals: List[LiveSignal] = []
        for row in odds_rows:
            features = self.feature_builder.build(row)
            trigger = self.micro_model.should_trigger(row, features)
            ev = self.micro_model.compute_ev(row, features)
            if not trigger and (ev is None or ev <= 0):
                continue
            signal = LiveSignal(
                event_id=row.get("game_id"),
                market=self.micro_model.__class__.__name__,
                odds=row.get("odds"),
                implied_prob=row.get("implied_prob"),
                ev=ev,
                features=features,
                timestamp=row.get("ts") or row.get("game_date"),
                stake=None,
                recommendation="BUY" if ev and ev > 0 else "HOLD",
            )
            signals.append(signal)
        return signals

