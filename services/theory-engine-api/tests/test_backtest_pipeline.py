import pytest

from engine.pipelines.backtest import BacktestPipeline
from engine.pipelines.interfaces import PipelineContext
from engine.common.result_schema import BacktestResult
from engine.common.micro_model import MicroModel
from engine.common.feature_builder import FeatureBuilder


class DummyLoader:
    async def load_games(self, league_id, seasons=None):
        return [
            {"game_id": "g1", "metrics": {"winner": "home"}},
            {"game_id": "g2", "metrics": {"winner": "away"}},
        ]


class DummyFeatureBuilder(FeatureBuilder):
    def required_fields(self):
        return []

    def build_minimal(self, event):
        return {"home_true_prob": 0.6, "away_true_prob": 0.4}

    def build_full(self, event):
        return self.build_minimal(event)


class AlwaysHomeModel(MicroModel):
    def should_trigger(self, event, features):
        return True

    def compute_ev(self, event, features):
        return 0.1

    def compute_outcome(self, result_data):
        return {"outcome": "win" if result_data.get("winner") == "home" else "loss", "pnl": 1.0}

    def generate_output_row(self, event, features, outcome=None, ev=None):
        return BacktestResult(
            event_id=event["game_id"],
            market="home_only",
            odds=None,
            implied_prob=None,
            ev=ev,
            outcome=outcome.get("outcome"),
            pnl=outcome.get("pnl"),
            features=features,
            timestamp=None,
        )


class CollectingRepo:
    def __init__(self):
        self.saved = []

    async def save_backtest(self, items):
        self.saved.extend(items)


@pytest.mark.asyncio
async def test_backtest_pipeline_chunks_and_saves():
    repo = CollectingRepo()
    pipeline = BacktestPipeline(
        loader=DummyLoader(),
        micro_model=AlwaysHomeModel(),
        feature_builder=DummyFeatureBuilder(mode="minimal"),
        results_repo=repo,
    )
    ctx = PipelineContext(league_id=1)
    await pipeline.run(ctx, chunk_size=1)

    # repo should have been called per chunk; saved contains all runs
    assert len(repo.saved) == 2
    markets = {r.market for r in repo.saved}
    assert "home_only" in markets

