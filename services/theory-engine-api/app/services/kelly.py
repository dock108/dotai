"""Kelly fraction helpers and recommendation mapping."""

from __future__ import annotations


def compute_kelly_fraction(win_prob: float, decimal_odds: float) -> float:
    """Compute Kelly fraction given win probability and decimal odds."""
    if decimal_odds <= 1 or win_prob <= 0 or win_prob >= 1:
        return 0.0
    edge = (win_prob * decimal_odds) - 1.0
    denom = decimal_odds - 1.0
    if denom <= 0:
        return 0.0
    return max(0.0, edge / denom)


def map_recommendation(kelly_fraction: float, edge: float) -> str:
    """Map Kelly/edge to recommendation bucket."""
    if kelly_fraction > 0.05 or edge > 0.08:
        return "strong"
    if kelly_fraction > 0.02 or edge > 0.03:
        return "lean"
    return "no_bet"

