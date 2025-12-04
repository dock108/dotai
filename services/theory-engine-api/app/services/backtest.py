"""30-day backtest utilities."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from .bet_performance import BetPerformance, StoredBetRow, compute_bet_performance


def run_30day_backtest(
    bets: List[StoredBetRow],
    bet_types: List[str],
) -> Dict[str, BetPerformance]:
    now = datetime.utcnow()
    cutoff = now - timedelta(days=30)

    def last_30d_filter(b: StoredBetRow) -> bool:
        try:
            dt = datetime.fromisoformat(b.event_date)
        except Exception:
            return False
        return dt >= cutoff

    results: Dict[str, BetPerformance] = {}
    for bt in bet_types:
        results[bt] = compute_bet_performance(bets, bt, last_30d_filter=last_30d_filter)
    return results

