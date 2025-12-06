from __future__ import annotations

from typing import Any, Mapping


def moneyline_outcome(result_data: Mapping[str, Any], stake: float, price: float) -> dict[str, Any]:
    """
    Compute moneyline outcome given result_data with winner ("home"/"away").
    Returns outcome (win/loss/push) and pnl.
    """
    winner = result_data.get("winner")
    if winner is None:
        return {"outcome": "void", "pnl": 0.0}
    outcome = "win" if winner == result_data.get("side") else "loss"
    pnl = stake * (price / 100) if price > 0 else stake * (100 / abs(price))
    if outcome == "win":
        return {"outcome": "win", "pnl": pnl}
    return {"outcome": "loss", "pnl": -stake}


def spread_outcome(result_data: Mapping[str, Any], stake: float, price: float, spread: float, is_home: bool) -> dict[str, Any]:
    """
    Compute spread outcome using margin_of_victory and spread.
    """
    if "margin_of_victory" not in result_data:
        return {"outcome": "void", "pnl": 0.0}
    mov = result_data["margin_of_victory"]
    signed_mov = mov if is_home else -mov
    cover_margin = signed_mov - spread
    if cover_margin > 0:
        outcome = "win"
        pnl = stake * (price / 100) if price > 0 else stake * (100 / abs(price))
    elif cover_margin == 0:
        outcome = "push"
        pnl = 0.0
    else:
        outcome = "loss"
        pnl = -stake
    return {"outcome": outcome, "pnl": pnl}


def total_outcome(result_data: Mapping[str, Any], stake: float, price: float, total: float, side: str) -> dict[str, Any]:
    """
    Compute total outcome using combined_score vs total.
    side: "over" or "under"
    """
    if "combined_score" not in result_data:
        return {"outcome": "void", "pnl": 0.0}
    combined = result_data["combined_score"]
    if side == "over":
        diff = combined - total
    else:
        diff = total - combined
    if diff > 0:
        outcome = "win"
        pnl = stake * (price / 100) if price > 0 else stake * (100 / abs(price))
    elif diff == 0:
        outcome = "push"
        pnl = 0.0
    else:
        outcome = "loss"
        pnl = -stake
    return {"outcome": outcome, "pnl": pnl}


