"""Merge LLM-inferred config with user overrides."""

from __future__ import annotations

from typing import Any, Dict


def build_model_config(inferred: Dict[str, Any], user_overrides: Dict[str, Any] | None) -> Dict[str, Any]:
    """Merge inferred config with user overrides (overrides win)."""
    user_overrides = user_overrides or {}
    merged = {
        "sport": inferred.get("sport"),
        "features": inferred.get("features", []),
        "bet_types": inferred.get("bet_types", []),
        "filters": inferred.get("filters", {}),
        "backtest_window_days": inferred.get("backtest_window_days", 30),
        "historical_seasons": inferred.get("historical_seasons", []),
        "simulation_horizon_days": inferred.get("simulation_horizon_days", 7),
        "p2p_fee_rate": inferred.get("p2p_fee_rate", 0.02),
        "p2p_target_buffer": inferred.get("p2p_target_buffer", 0.02),
    }
    for key, value in user_overrides.items():
        if value is not None:
            merged[key] = value
    return merged

