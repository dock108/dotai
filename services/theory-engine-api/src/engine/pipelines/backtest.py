from __future__ import annotations

from typing import Any, Dict, Iterable, List

from engine.common.micro_model import MicroModel
from engine.common.result_schema import BacktestResult
from engine.common.feature_builder import FeatureBuilder
from .interfaces import GameLoader, ResultsRepository, PipelineContext


class BacktestPipeline:
    """
    Historical bet placement simulation.
    """

    def __init__(
        self,
        loader: GameLoader,
        micro_model: MicroModel,
        feature_builder: FeatureBuilder,
        results_repo: ResultsRepository | None = None,
    ):
        self.loader = loader
        self.micro_model = micro_model
        self.feature_builder = feature_builder
        self.results_repo = results_repo

    async def run(self, ctx: PipelineContext, chunk_size: int | None = None) -> List[BacktestResult]:
        games = list(await self.loader.load_games(ctx.league_id, ctx.seasons))
        results: List[BacktestResult] = []

        def _chunks(seq, size):
            for i in range(0, len(seq), size):
                yield seq[i : i + size]

        batches = _chunks(games, chunk_size) if chunk_size else [games]

        for batch in batches:
            for game in batch:
                features = self.feature_builder.build(game)
                if not self.micro_model.should_trigger(game, features):
                    continue
                ev = self.micro_model.compute_ev(game, features)
                outcome = self.micro_model.compute_outcome(game.get("metrics", {}))
                result = self.micro_model.generate_output_row(game, features, outcome=outcome, ev=ev)
                results.append(result)

            if chunk_size and self.results_repo and results:
                await self.results_repo.save_backtest(results)
                results = []

        if self.results_repo and results:
            await self.results_repo.save_backtest(results)
        return results

