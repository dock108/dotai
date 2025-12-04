"""Historical performance calculations by bet type."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta

from .bet_performance import BetPerformance, StoredBetRow, compute_bet_performance


def compute_historical_performance(
    bets: list[StoredBetRow],
    bet_types: list[str],
) -> list[BetPerformance]:
    """Compute performance across bet types for full history and theory subset."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=30)

    def last_30d_filter(b: StoredBetRow) -> bool:
        try:
            dt = datetime.fromisoformat(b.event_date)
        except Exception:
            return False
        return dt >= cutoff

    performances: list[BetPerformance] = []
    for bt in bet_types:
        performances.append(compute_bet_performance(bets, bt, last_30d_filter=last_30d_filter))
    return performances

