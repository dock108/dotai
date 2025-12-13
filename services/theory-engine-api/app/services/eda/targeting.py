from __future__ import annotations

from typing import Any

from ..feature_metadata import FeatureTiming, get_feature_metadata  # re-export convenience if needed


def resolve_target_definition(req_target: str | None, target_def: Any) -> Any:
    """Target definition must be provided explicitly."""
    if target_def is not None:
        return target_def
    raise ValueError("target_definition is required")


def target_value(metrics: dict[str, Any], target_def: Any) -> float | str | None:
    """Compute target label per TargetDefinition (stat or market)."""
    # Convert Pydantic model to dict if needed
    if target_def is None:
        tdef = {}
    elif hasattr(target_def, "model_dump"):
        tdef = target_def.model_dump()
    elif hasattr(target_def, "dict"):
        tdef = target_def.dict()
    else:
        tdef = target_def
    tclass = tdef.get("target_class")
    tname = tdef.get("target_name")
    mt = tdef.get("market_type")
    side = tdef.get("side")

    if tclass == "stat":
        if tname == "home_points":
            return metrics.get("home_score")
        if tname == "away_points":
            return metrics.get("away_score")
        if tname == "combined_score":
            return metrics.get("combined_score")
        if tname == "margin_of_victory":
            return metrics.get("margin_of_victory")
        if tname == "winner":
            winner = metrics.get("winner")
            if winner in {"home", "away"}:
                return 1.0 if winner == "home" else 0.0
            return None
        return None

    if tclass == "market":
        if mt == "spread":
            if side == "home":
                val = metrics.get("did_home_cover")
                return 1.0 if val else 0.0 if val is not None else None
            val = metrics.get("did_away_cover")
            return 1.0 if val else 0.0 if val is not None else None
        if mt == "moneyline":
            winner = metrics.get("winner")
            if winner not in {"home", "away"}:
                return None
            return 1.0 if winner == side else 0.0
        if mt == "total":
            total_result = metrics.get("total_result")
            if total_result not in {"over", "under"}:
                return None
            return 1.0 if total_result == side else 0.0
    return None


