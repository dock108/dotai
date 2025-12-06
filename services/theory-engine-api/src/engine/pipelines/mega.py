from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence

from engine.common.result_schema import BacktestResult
from engine.common.feature_builder import FeatureBuilder
from engine.common.micro_model import MicroModel
from .interfaces import PipelineContext
from engine.common.utils import implied_probability


class MegaPipeline:
    """
    Build training matrix from micro-model results + closing odds + scores.
    """

    def __init__(self, feature_builder: FeatureBuilder):
        self.feature_builder = feature_builder

    async def run(
        self,
        ctx: PipelineContext,
        micro_results: Sequence[BacktestResult],
        closing_odds: Dict[Any, Dict[str, Any]],
        results: Dict[Any, Dict[str, Any]],
    ) -> Dict[str, Any]:
        matrix: List[Dict[str, Any]] = []
        for row in micro_results:
            game_id = row.event_id
            base = {
                "game_id": game_id,
                "market": row.market,
                "ev": row.ev,
                "pnl": row.pnl,
                "outcome": row.outcome,
                "odds": row.odds,
                "implied_prob": row.implied_prob or implied_probability(row.odds, "decimal") if row.odds else None,
            }
            closing = closing_odds.get(game_id, {})
            final = results.get(game_id, {})
            features = self.feature_builder.build(
                {
                    "game_id": game_id,
                    "closing": closing,
                    "result": final,
                    "metadata": {"league_id": ctx.league_id},
                    "features": row.features,
                }
            )
            matrix.append({**base, **closing, **final, **(features or {})})

        # Placeholder for training: return matrix to upstream trainer
        return {
            "matrix": matrix,
            "rows": len(matrix),
        }

