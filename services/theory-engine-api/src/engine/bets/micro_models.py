from __future__ import annotations

from typing import Any, Dict, Mapping

from ..common.micro_model import MicroModel
from ..common.result_schema import BacktestResult
from ..common.utils import ev_from_price, implied_probability
from ..common.utils.outcomes import moneyline_outcome, spread_outcome, total_outcome
from ..theories.registry import register_theory


@register_theory("closing_moneyline_home")
@register_theory("closing_moneyline_away")
class ClosingMoneylineModel(MicroModel):
    """Moneyline model using closing prices and a provided true_prob feature."""

    def __init__(self, side: str):
        self.side = side  # "home" or "away"

    def should_trigger(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> bool:
        return f"closing_ml_{self.side}" in event

    def compute_ev(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> float | None:
        price = event.get(f"closing_ml_{self.side}")
        true_prob = features.get(f"{self.side}_true_prob") or features.get("true_prob")
        return ev_from_price(true_prob, price)

    def compute_outcome(self, result_data: Mapping[str, Any]) -> Dict[str, Any]:
        # expects result_data to include winner and closing_ml_<side>
        price = result_data.get(f"closing_ml_{self.side}")
        if price is None:
            return {"outcome": "void", "pnl": 0.0}
        return moneyline_outcome(
            {**result_data, "side": self.side},
            stake=1.0,
            price=price,
        )

    def generate_output_row(
        self,
        event: Mapping[str, Any],
        features: Mapping[str, Any],
        ev: float | None,
        outcome: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        price = event.get(f"closing_ml_{self.side}")
        return BacktestResult(
            event_id=str(event.get("game_id", "")),
            market=f"moneyline_{self.side}",
            stake=1.0,
            odds=price,
            implied_prob=implied_probability(price),
            ev=ev,
            features=dict(features),
            outcome=outcome.get("outcome") if outcome else None,
            pnl=outcome.get("pnl") if outcome else None,
        ).model_dump()


@register_theory("closing_spread_home")
@register_theory("closing_spread_away")
class ClosingSpreadModel(MicroModel):
    """Spread model using closing lines."""

    def __init__(self, side: str):
        self.side = side  # "home" or "away"

    def should_trigger(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> bool:
        return f"closing_spread_{self.side}" in event

    def compute_ev(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> float | None:
        price = event.get(f"closing_spread_{self.side}_price")
        cover_prob = features.get(f"{self.side}_cover_prob") or features.get("cover_prob")
        return ev_from_price(cover_prob, price)

    def compute_outcome(self, result_data: Mapping[str, Any]) -> Dict[str, Any]:
        spread = result_data.get(f"closing_spread_{self.side}")
        price = result_data.get(f"closing_spread_{self.side}_price")
        if spread is None or price is None:
            return {"outcome": "void", "pnl": 0.0}
        is_home = self.side == "home"
        return spread_outcome(result_data, stake=1.0, price=price, spread=spread, is_home=is_home)

    def generate_output_row(
        self,
        event: Mapping[str, Any],
        features: Mapping[str, Any],
        ev: float | None,
        outcome: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        price = event.get(f"closing_spread_{self.side}_price")
        return BacktestResult(
            event_id=str(event.get("game_id", "")),
            market=f"spread_{self.side}",
            stake=1.0,
            odds=price,
            implied_prob=implied_probability(price),
            ev=ev,
            features=dict(features),
            outcome=outcome.get("outcome") if outcome else None,
            pnl=outcome.get("pnl") if outcome else None,
        ).model_dump()


@register_theory("closing_total_over")
@register_theory("closing_total_under")
class ClosingTotalModel(MicroModel):
    """Totals model using closing total and provided over/under probabilities."""

    def __init__(self, side: str):
        self.side = side  # "over" or "under"

    def should_trigger(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> bool:
        return "closing_total" in event

    def compute_ev(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> float | None:
        price = event.get("closing_total_price")
        prob = features.get(f"prob_{self.side}") or features.get("total_prob")
        return ev_from_price(prob, price)

    def compute_outcome(self, result_data: Mapping[str, Any]) -> Dict[str, Any]:
        total = result_data.get("closing_total")
        price = result_data.get("closing_total_price")
        if total is None or price is None:
            return {"outcome": "void", "pnl": 0.0}
        return total_outcome(result_data, stake=1.0, price=price, total=total, side=self.side)

    def generate_output_row(
        self,
        event: Mapping[str, Any],
        features: Mapping[str, Any],
        ev: float | None,
        outcome: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        price = event.get("closing_total_price")
        return BacktestResult(
            event_id=str(event.get("game_id", "")),
            market=f"total_{self.side}",
            stake=1.0,
            odds=price,
            implied_prob=implied_probability(price),
            ev=ev,
            features=dict(features),
            outcome=outcome.get("outcome") if outcome else None,
            pnl=outcome.get("pnl") if outcome else None,
        ).model_dump()


@register_theory("closing_line_underdog")
class UnderdogAngleModel(MicroModel):
    """Simple angle: back moneyline underdogs above a threshold."""

    def __init__(self, side: str = "away", threshold_decimal: float = 2.5):
        self.side = side
        self.threshold_decimal = threshold_decimal

    def should_trigger(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> bool:
        price = event.get(f"closing_ml_{self.side}")
        if price is None:
            return False
        # convert American to decimal
        dec = (price / 100) + 1 if price > 0 else (100 / abs(price)) + 1
        return dec >= self.threshold_decimal

    def compute_ev(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> float | None:
        price = event.get(f"closing_ml_{self.side}")
        prob = features.get(f"{self.side}_true_prob") or features.get("true_prob")
        return ev_from_price(prob, price)

    def compute_outcome(self, result_data: Mapping[str, Any]) -> Dict[str, Any]:
        price = result_data.get(f"closing_ml_{self.side}")
        if price is None:
            return {"outcome": "void", "pnl": 0.0}
        return moneyline_outcome(
            {**result_data, "side": self.side},
            stake=1.0,
            price=price,
        )

    def generate_output_row(
        self,
        event: Mapping[str, Any],
        features: Mapping[str, Any],
        ev: float | None,
        outcome: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        price = event.get(f"closing_ml_{self.side}")
        return BacktestResult(
            event_id=str(event.get("game_id", "")),
            market=f"underdog_ml_{self.side}",
            stake=1.0,
            odds=price,
            implied_prob=implied_probability(price),
            ev=ev,
            features=dict(features),
            outcome=outcome.get("outcome") if outcome else None,
            pnl=outcome.get("pnl") if outcome else None,
        ).model_dump()


