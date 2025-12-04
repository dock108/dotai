"""Bet performance calculations using decimal odds."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel


class StoredBetRow(BaseModel):
    game_id: str
    bet_type: str
    selection: str
    market_decimal_odds: float
    result: Literal["W", "L", "P"]
    theory_flag: bool
    event_date: str


class BetPerformanceSlice(BaseModel):
    n_bets: int
    record: dict
    pnl_units: float
    roi: float


class BetPerformance(BaseModel):
    bet_type: str
    historical_all: BetPerformanceSlice
    historical_theory_subset: BetPerformanceSlice
    last_30_days: BetPerformanceSlice


def _calc_slice(bets: list[StoredBetRow]) -> BetPerformanceSlice:
    wins = losses = pushes = 0
    pnl = 0.0
    for bet in bets:
        if bet.result == "W":
            wins += 1
            pnl += bet.market_decimal_odds - 1.0
        elif bet.result == "L":
            losses += 1
            pnl -= 1.0
        elif bet.result == "P":
            pushes += 1
            # pnl unchanged
    n_bets = len(bets)
    roi = pnl / n_bets if n_bets else 0.0
    return BetPerformanceSlice(
        n_bets=n_bets,
        record={"wins": wins, "losses": losses, "pushes": pushes},
        pnl_units=round(pnl, 4),
        roi=round(roi, 4),
    )


def compute_bet_performance(
    bets: list[StoredBetRow],
    bet_type: str,
    *,
    last_30d_filter,
) -> BetPerformance:
    """Compute performance slices for a given bet type."""
    bets_bt = [b for b in bets if b.bet_type == bet_type]
    theory_bets = [b for b in bets_bt if b.theory_flag]
    last_30_bets = [b for b in bets_bt if last_30d_filter(b)]

    return BetPerformance(
        bet_type=bet_type,
        historical_all=_calc_slice(bets_bt),
        historical_theory_subset=_calc_slice(theory_bets),
        last_30_days=_calc_slice(last_30_bets),
    )

