from __future__ import annotations

from typing import Any, Sequence
import random
import statistics


def simulate_historical_mc(rows: Sequence[Any]) -> dict[str, Any]:
    """Lightweight MC over historical micro rows to estimate luck vs expectation.

    Assumptions (kept simple and explicit):
    - Bet sizing: 1 unit flat
    - Ordering: chronological as provided
    - Independence: assumed (no covariance modeled)
    """
    if not rows:
        return {"runs": 0, "mean_pnl": 0.0, "p5_pnl": 0.0, "p50_pnl": 0.0, "p95_pnl": 0.0, "luck_score": 0.0}

    sims = 200
    pnl_samples: list[float] = []
    win_probs = []
    for r in rows:
        implied = getattr(r, "implied_prob", None)
        outcome = getattr(r, "outcome", None)
        if implied is not None:
            win_probs.append(float(implied))
        elif outcome in {"win", "loss"}:
            win_probs.append(0.5)
    base_prob = statistics.mean(win_probs) if win_probs else 0.5

    for _ in range(sims):
        acc = 0.0
        for _r in rows:
            implied = getattr(_r, "implied_prob", None)
            p = implied if implied is not None else base_prob
            acc += 1.0 if random.random() < p else -1.0
        pnl_samples.append(acc)

    pnl_samples.sort()
    actual = sum(getattr(r, "pnl_units", 0.0) or 0.0 for r in rows)
    mean_pnl = statistics.mean(pnl_samples) if pnl_samples else 0.0
    p5 = pnl_samples[int(0.05 * len(pnl_samples))] if pnl_samples else 0.0
    p50 = pnl_samples[int(0.50 * len(pnl_samples))] if pnl_samples else 0.0
    p95 = pnl_samples[int(0.95 * len(pnl_samples)) - 1] if pnl_samples else 0.0
    luck_score = actual - mean_pnl

    return {
        "runs": sims,
        "mean_pnl": mean_pnl,
        "p5_pnl": p5,
        "p50_pnl": p50,
        "p95_pnl": p95,
        "actual_pnl": actual,
        "luck_score": luck_score,
    }

