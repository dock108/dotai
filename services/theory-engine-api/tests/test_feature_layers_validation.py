from engine.common.feature_layers import (
    CombinedFeatureBuilder,
    Level0RequiredBuilder,
    Level1DomainBuilder,
)


class BoomBuilder(Level1DomainBuilder):
    def build_minimal(self, event):
        raise RuntimeError("fail")

    def build_full(self, event):
        raise RuntimeError("fail")


def test_combined_feature_builder_gracefully_handles_failures():
    level0 = Level0RequiredBuilder(mode="minimal")
    failing = BoomBuilder(mode="minimal")
    combo = CombinedFeatureBuilder([failing, level0], mode="minimal")
    event = {
        "closing": {"closing_ml_home": -120},
        "lines": {"closing_total": 210},
        "result": {"home_score": 100, "away_score": 90},
        "metadata": {"game_id": 1},
    }
    out = combo.build(event)
    assert out["closing_ml_home"] == -120
    assert "closing_total" in out




