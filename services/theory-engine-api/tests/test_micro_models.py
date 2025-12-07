import pytest

from engine.bets.micro_models import (
    ClosingMoneylineModel,
    ClosingSpreadModel,
    ClosingTotalModel,
    UnderdogAngleModel,
)


def test_closing_moneyline_ev_and_outcome_win():
    model = ClosingMoneylineModel(side="home")
    event = {"game_id": "g1", "closing_ml_home": 150}
    features = {"home_true_prob": 0.45}

    ev = model.compute_ev(event, features)
    assert ev is not None and ev > 0  # positive edge

    outcome = model.compute_outcome({"winner": "home", "closing_ml_home": 150})
    assert outcome["outcome"] == "win"
    assert outcome["pnl"] > 0


def test_closing_spread_trigger_and_push():
    model = ClosingSpreadModel(side="away")
    event = {"game_id": "g2", "closing_spread_away": -3.5, "closing_spread_away_price": -110}
    features = {"away_cover_prob": 0.52}
    assert model.should_trigger(event, features)

    outcome = model.compute_outcome(
        {"margin_of_victory": -3.5, "closing_spread_away": -3.5, "closing_spread_away_price": -110}
    )
    assert outcome["outcome"] == "push"
    assert outcome["pnl"] == 0.0


def test_closing_total_under_loss():
    model = ClosingTotalModel(side="under")
    event = {"game_id": "g3", "closing_total": 220.5, "closing_total_price": -110}
    features = {"prob_under": 0.47}
    outcome = model.compute_outcome({"combined_score": 230, "closing_total": 220.5, "closing_total_price": -110})
    assert outcome["outcome"] == "loss"
    assert outcome["pnl"] < 0


def test_underdog_angle_threshold():
    model = UnderdogAngleModel(side="away", threshold_decimal=2.5)
    event = {"game_id": "g4", "closing_ml_away": 300}
    assert model.should_trigger(event, {})
    event_low = {"game_id": "g4", "closing_ml_away": 120}
    assert not model.should_trigger(event_low, {})



