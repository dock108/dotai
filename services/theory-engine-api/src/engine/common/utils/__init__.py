from __future__ import annotations

from math import exp
from typing import Any, Iterable, List, Mapping, Tuple


# Odds / EV ------------------------------------------------------------

def american_to_decimal(price: float | None) -> float | None:
    if price is None:
        return None
    if price > 0:
        return (price / 100) + 1
    if price < 0:
        return (100 / abs(price)) + 1
    return None


def implied_probability(price: float | None) -> float | None:
    if price is None or price == 0:
        return None
    if price > 0:
        return 100 / (price + 100)
    return -price / (-price + 100)


def ev_from_price(prob: float | None, price: float | None) -> float | None:
    """Expected value given win probability and American odds price."""
    if prob is None or price is None:
        return None
    # payout: +price on 100 risk for positive odds; 100/|price| risk to win 100 on negative odds
    if price > 0:
        payout = price / 100
        risk = 1.0
    else:
        payout = 1.0
        risk = abs(price) / 100
    return prob * payout - (1 - prob) * risk


def ev_from_decimal(prob: float | None, decimal_odds: float | None) -> float | None:
    if prob is None or decimal_odds is None:
        return None
    payout = decimal_odds - 1.0
    return prob * payout - (1 - prob) * 1.0


# Imputation ----------------------------------------------------------

def coalesce_numeric(*vals: Any) -> float | None:
    for v in vals:
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


# Windowing -----------------------------------------------------------

def rolling_window(values: List[float], window: int) -> List[float]:
    if window <= 0:
        return []
    out: List[float] = []
    acc: List[float] = []
    for v in values:
        acc.append(v)
        if len(acc) > window:
            acc.pop(0)
        out.append(sum(acc) / len(acc))
    return out


# Validation ----------------------------------------------------------

def require_keys(payload: Mapping[str, Any], keys: Iterable[str]) -> None:
    missing = [k for k in keys if k not in payload]
    if missing:
        raise ValueError(f"Missing required keys: {missing}")


# Feature merging -----------------------------------------------------

def merge_features(*feature_maps: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for fm in feature_maps:
        merged.update({k: v for k, v in fm.items() if v is not None})
    return merged

