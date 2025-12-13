from __future__ import annotations

from typing import Any, Dict, List, Tuple


def apply_exposure_controls(
    micro_rows: List[Any],
    *,
    controls: Any,
    target_def: Dict[str, Any],
) -> Tuple[List[Any], Dict[str, Any], List[dict[str, Any]]]:
    ctl = controls or {}
    max_bets_per_day = ctl.get("max_bets_per_day", 5)
    max_per_side = ctl.get("max_bets_per_side_per_day")
    spread_abs_min = ctl.get("spread_abs_min")
    spread_abs_max = ctl.get("spread_abs_max")

    candidates: List[Any] = [r for r in micro_rows if bool(getattr(r, "trigger_flag", False))]
    dropped: List[dict[str, Any]] = []

    if target_def.get("market_type") == "spread" and (spread_abs_min is not None or spread_abs_max is not None):
        kept: List[Any] = []
        for r in candidates:
            line = getattr(r, "closing_line", None)
            if line is None:
                dropped.append({"game_id": getattr(r, "game_id", None), "reason": "missing_line_for_spread_band"})
                continue
            abs_line = abs(float(line))
            if spread_abs_min is not None and abs_line < float(spread_abs_min):
                dropped.append({"game_id": getattr(r, "game_id", None), "reason": "spread_band_low", "abs_line": abs_line})
                continue
            if spread_abs_max is not None and abs_line > float(spread_abs_max):
                dropped.append({"game_id": getattr(r, "game_id", None), "reason": "spread_band_high", "abs_line": abs_line})
                continue
            kept.append(r)
        candidates = kept

    by_day: Dict[str, List[Any]] = {}
    for r in candidates:
        day = None
        meta = getattr(r, "meta", None)
        if isinstance(meta, dict):
            day = meta.get("game_date")
        if isinstance(day, str) and len(day) >= 10:
            day = day[:10]
        else:
            day = "unknown"
        by_day.setdefault(day, []).append(r)

    selected: List[Any] = []
    for day, rows in by_day.items():
        rows_sorted = sorted(rows, key=lambda rr: (getattr(rr, "edge_vs_implied", None) is None, -(getattr(rr, "edge_vs_implied", 0.0) or 0.0)))
        take = rows_sorted
        if max_bets_per_day is not None:
            take = take[: int(max_bets_per_day)]

        if max_per_side is not None:
            per_side: Dict[str, int] = {}
            filtered_take: List[Any] = []
            for r in take:
                side = getattr(r, "side", "unknown") or "unknown"
                per_side.setdefault(side, 0)
                if per_side[side] >= int(max_per_side):
                    dropped.append({"game_id": getattr(r, "game_id", None), "reason": "max_per_side_per_day", "day": day, "side": side})
                    continue
                per_side[side] += 1
                filtered_take.append(r)
            take = filtered_take

        if max_bets_per_day is not None and len(rows_sorted) > len(take):
            for r in rows_sorted[len(take):]:
                dropped.append({"game_id": getattr(r, "game_id", None), "reason": "max_bets_per_day", "day": day})

        selected.extend(take)

    selected_ids = {getattr(r, "game_id", None) for r in selected}
    for r in micro_rows:
        meta = getattr(r, "meta", None)
        if meta is None:
            r.meta = {}
        if isinstance(r.meta, dict):
            r.meta["selected_bet"] = getattr(r, "game_id", None) in selected_ids

    total_triggered = len([r for r in micro_rows if getattr(r, "trigger_flag", False)])
    total_selected = len(selected)
    days = len(by_day)
    by_side: Dict[str, int] = {}
    for r in selected:
        side = getattr(r, "side", None)
        by_side[side] = by_side.get(side, 0) + 1
    summary = {
        "triggered": total_triggered,
        "selected": total_selected,
        "dropped_due_to_controls": max(0, total_triggered - total_selected),
        "unique_days": days,
        "avg_bets_per_day": (total_selected / days) if days else 0.0,
        "by_side": by_side,
        "notes": [
            "Selection ranks by edge_vs_implied within each day; missing edge ranks last.",
            "This is a historical selection simulation (artifact), not a deployable execution engine.",
        ],
    }
    warnings: List[str] = []
    if max_bets_per_day is not None and total_triggered > total_selected:
        warnings.append("Exposure controls capped daily bet count; results may reflect throttling rather than signal scarcity.")
    if any(d.get("reason") in {"spread_band_low", "spread_band_high"} for d in dropped):
        warnings.append("Spread band gating removed triggered bets; be careful interpreting improvements as 'edge' vs filter artifact.")
    summary["warnings"] = warnings
    return selected, summary, dropped


def build_bet_tape(selected: List[Any]) -> List[dict[str, Any]]:
    if not selected:
        return []
    ranked = sorted(selected, key=lambda r: (getattr(r, "edge_vs_implied", None) is None, -(getattr(r, "edge_vs_implied", 0.0) or 0.0)))
    top = ranked[:5]
    bottom = list(reversed(ranked))[:5] if len(ranked) > 5 else []
    tape: List[dict[str, Any]] = []
    for r in top:
        tape.append(
            {
                "strength": "strong",
                "game_id": getattr(r, "game_id", None),
                "date": (getattr(r, "meta", {}) or {}).get("game_date"),
                "side": getattr(r, "side", None),
                "line": getattr(r, "closing_line", None),
                "odds": getattr(r, "closing_odds", None),
                "model_prob": getattr(r, "model_prob", None),
                "implied_prob": getattr(r, "implied_prob", None),
                "edge": getattr(r, "edge_vs_implied", None),
                "outcome": getattr(r, "outcome", None),
                "pnl_units": getattr(r, "pnl_units", None),
                "why": ((getattr(r, "meta", {}) or {}).get("trigger_reasons") or [""])[0],
            }
        )
    for r in bottom:
        tape.append(
            {
                "strength": "marginal",
                "game_id": getattr(r, "game_id", None),
                "date": (getattr(r, "meta", {}) or {}).get("game_date"),
                "side": getattr(r, "side", None),
                "line": getattr(r, "closing_line", None),
                "odds": getattr(r, "closing_odds", None),
                "model_prob": getattr(r, "model_prob", None),
                "implied_prob": getattr(r, "implied_prob", None),
                "edge": getattr(r, "edge_vs_implied", None),
                "outcome": getattr(r, "outcome", None),
                "pnl_units": getattr(r, "pnl_units", None),
                "why": ((getattr(r, "meta", {}) or {}).get("trigger_reasons") or [""])[0],
            }
        )
    return tape[:10]


