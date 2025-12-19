from engine.pipelines.mega import MegaPipeline
from engine.common.feature_builder import FeatureBuilder
from engine.common.result_schema import BacktestResult
from engine.pipelines.interfaces import PipelineContext


class PassthroughFeatureBuilder(FeatureBuilder):
    def required_fields(self):
        return []

    def build_minimal(self, event):
        return {"f1": 1.0, "f2": 2.0, **event.get("features", {})}

    def build_full(self, event):
        return self.build_minimal(event)


def test_mega_pipeline_snapshot():
    pipeline = MegaPipeline(feature_builder=PassthroughFeatureBuilder(mode="minimal"))
    ctx = PipelineContext(league_id=7)

    micro_results = [
        BacktestResult(
            event_id="g1",
            market="moneyline_home",
            odds=2.1,
            implied_prob=0.48,
            ev=0.05,
            outcome=1.0,
            pnl=1.0,
            features={"extra": 9},
            timestamp=None,
        )
    ]
    closing_odds = {"g1": {"closing_ml_home": -110}}
    results = {"g1": {"winner": "home", "combined_score": 210}}

    out = pipeline.run(ctx, micro_results, closing_odds, results)
    assert out["rows"] == 1
    matrix_row = out["matrix"][0]
    expected_keys = {"game_id", "market", "ev", "pnl", "outcome", "odds", "implied_prob", "closing_ml_home", "winner", "combined_score", "f1", "f2", "extra"}
    assert expected_keys.issubset(set(matrix_row.keys()))
    assert matrix_row["game_id"] == "g1"




