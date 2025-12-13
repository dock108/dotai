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


def implied_probability_from_american(american_odds: float | None) -> float | None:
    """Return implied win probability from American odds."""
    if american_odds is None or american_odds == 0:
        return None
    if american_odds > 0:
        return round(100.0 / (american_odds + 100.0), 4)
    return round((-american_odds) / ((-american_odds) + 100.0), 4)


def profit_for_american_odds(american_odds: float, risk_units: float = 1.0) -> float:
    """
    Profit (not including stake) for a winning bet risking `risk_units` at the given American odds.
    Loss is always `-risk_units` when the bet loses.
    """
    dec = american_to_decimal(american_odds)
    if dec is None:
        return 0.0
    return (dec - 1.0) * risk_units

