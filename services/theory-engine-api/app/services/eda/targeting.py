from __future__ import annotations

from typing import Any

from ..feature_metadata import FeatureTiming, get_feature_metadata  # re-export convenience if needed


def resolve_target_definition(req_target: str | None, target_def: Any) -> Any:
    """Back-compat helper to normalize target definition."""
    if target_def is not None:
        return target_def
    if req_target == "win":
        return {"market_type": "moneyline", "side": "home", "odds_assumption": "use_closing"}
    if req_target == "over":
        return {"market_type": "total", "side": "over", "odds_assumption": "use_closing"}
    return {"market_type": "spread", "side": "home", "odds_assumption": "use_closing"}


def target_value(metrics: dict[str, Any], target_def: Any) -> float | None:
    """Compute target label per TargetDefinition."""
    # Convert Pydantic model to dict if needed
    if target_def is None:
        tdef = {}
    elif hasattr(target_def, "model_dump"):
        tdef = target_def.model_dump()
    elif hasattr(target_def, "dict"):
        tdef = target_def.dict()
    else:
        tdef = target_def
    mt = tdef.get("market_type")
    side = tdef.get("side")
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


