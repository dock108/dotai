"""P2P market-maker pricing helpers."""

from __future__ import annotations


def suggested_p2p_price(win_prob: float, fee_rate: float, buffer: float) -> float:
    """Compute suggested maker price (decimal) targeting positive EV after fees."""
    if win_prob <= 0 or win_prob >= 1 or fee_rate >= 1:
        return 0.0
    numerator = buffer + 1 - win_prob
    denom = win_prob * (1 - fee_rate)
    if denom <= 0:
        return 0.0
    d_post = 1 + numerator / denom
    return round(d_post, 4)


def compute_mm_ev(win_prob: float, posted_decimal_odds: float, fee_rate: float) -> float:
    """Compute expected value for maker after fees at posted odds."""
    if posted_decimal_odds <= 1 or win_prob <= 0 or win_prob >= 1:
        return 0.0
    win_leg = (posted_decimal_odds - 1) * (1 - fee_rate)
    ev = win_prob * win_leg - (1 - win_prob)
    return round(ev, 4)


def clamp_posted_odds(posted_odds: float, market_odds: float, max_diff_pct: float = 0.2) -> float:
    """Clamp posted odds to avoid giving away more than max_diff_pct edge vs market."""
    if market_odds <= 1:
        return posted_odds
    max_odds = market_odds * (1 + max_diff_pct)
    return min(posted_odds, max_odds)

