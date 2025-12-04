"""Odds conversion utilities."""

from __future__ import annotations


def american_to_decimal(american_odds: float | None) -> float | None:
    """Convert American odds to decimal odds.

    Positive odds: (odds / 100) + 1
    Negative odds: (100 / abs(odds)) + 1
    """
    if american_odds is None:
        return None
    if american_odds > 0:
        return round((american_odds / 100.0) + 1.0, 4)
    if american_odds < 0:
        return round((100.0 / abs(american_odds)) + 1.0, 4)
    return None


def decimal_to_american(decimal_odds: float | None) -> float | None:
    """Convert decimal odds to American odds."""
    if decimal_odds is None or decimal_odds <= 1:
        return None
    if decimal_odds >= 2:
        return round((decimal_odds - 1.0) * 100.0, 0)
    return round(-100.0 / (decimal_odds - 1.0), 0)


def implied_probability_from_decimal(decimal_odds: float | None) -> float | None:
    """Return implied win probability from decimal odds."""
    if decimal_odds is None or decimal_odds <= 1:
        return None
    return round(1.0 / decimal_odds, 4)

