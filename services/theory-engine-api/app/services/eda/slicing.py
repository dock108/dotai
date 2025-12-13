from __future__ import annotations

from typing import Any, List

import numpy as np


def slice_metrics(rows: List[Any]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for r in rows if getattr(r, "outcome", None) == "win")
    losses = sum(1 for r in rows if getattr(r, "outcome", None) == "loss")
    pushes = sum(1 for r in rows if getattr(r, "outcome", None) == "push")
    pnl = float(sum((getattr(r, "pnl_units", 0.0) or 0.0) for r in rows))
    roi = (pnl / n) if n else 0.0
    model_ps = [getattr(r, "model_prob", None) for r in rows if getattr(r, "model_prob", None) is not None]
    implied_ps = [getattr(r, "implied_prob", None) for r in rows if getattr(r, "implied_prob", None) is not None]
    edges = [getattr(r, "edge_vs_implied", None) for r in rows if getattr(r, "edge_vs_implied", None) is not None]
    hit_rate = wins / n if n else 0.0
    implied_avg = float(np.mean(implied_ps)) if implied_ps else None
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate": hit_rate,
        "pnl_units": pnl,
        "roi_units_per_bet": roi,
        "avg_model_prob": float(np.mean(model_ps)) if model_ps else None,
        "avg_implied_prob": implied_avg,
        "avg_edge": float(np.mean(edges)) if edges else None,
        "hit_minus_implied": (hit_rate - implied_avg) if implied_avg is not None else None,
    }


def build_performance_slices(selected_bets: List[Any], target_def: dict[str, Any]) -> dict[str, Any]:
    base = slice_metrics(selected_bets)

    def red_zone(m: dict[str, Any]) -> bool:
        if m.get("roi_units_per_bet") is not None and float(m["roi_units_per_bet"]) < 0:
            return True
        hmi = m.get("hit_minus_implied")
        return (hmi is not None) and (float(hmi) < 0)

    buckets = [
        ("p>=0.60", lambda r: (getattr(r, "model_prob", None) is not None and getattr(r, "model_prob") >= 0.60)),
        ("0.55-0.60", lambda r: (getattr(r, "model_prob", None) is not None and 0.55 <= getattr(r, "model_prob") < 0.60)),
        ("0.50-0.55", lambda r: (getattr(r, "model_prob", None) is not None and 0.50 <= getattr(r, "model_prob") < 0.55)),
    ]
    confidence = []
    for label, pred in buckets:
        rs = [r for r in selected_bets if pred(r)]
        m = slice_metrics(rs)
        m["label"] = label
        m["red_zone"] = red_zone(m)
        confidence.append(m)

    spread_buckets = []
    fav_ud = []
    if target_def.get("market_type") == "spread":
        spread_defs = [
            ("abs_line<3", lambda a: a < 3),
            ("3<=abs_line<6", lambda a: 3 <= a < 6),
            ("6<=abs_line<10", lambda a: 6 <= a < 10),
            ("abs_line>=10", lambda a: a >= 10),
        ]
        for label, f in spread_defs:
            rs = []
            for r in selected_bets:
                line = getattr(r, "closing_line", None)
                if line is None:
                    continue
                a = abs(float(line))
                if f(a):
                    rs.append(r)
            m = slice_metrics(rs)
            m["label"] = label
            m["red_zone"] = red_zone(m)
            spread_buckets.append(m)

        fav = []
        dog = []
        for r in selected_bets:
            line = getattr(r, "closing_line", None)
            if line is None:
                continue
            line = float(line)
            side = getattr(r, "side", None)
            if side == "home":
                (fav if line < 0 else dog).append(r)
            elif side == "away":
                (fav if line > 0 else dog).append(r)
        for label, rs in (("favorite", fav), ("underdog", dog)):
            m = slice_metrics(rs)
            m["label"] = label
            m["red_zone"] = red_zone(m)
            fav_ud.append(m)

    pace_vals: List[tuple[float, Any]] = []
    for r in selected_bets:
        pace = None
        feats = getattr(r, "features", None)
        if isinstance(feats, dict):
            pace = feats.get("pace_game")
        if pace is None:
            continue
        try:
            pace_f = float(pace)
        except (TypeError, ValueError):
            continue
        pace_vals.append((pace_f, r))
    pace_slices = []
    if len(pace_vals) >= 20:
        pace_vals.sort(key=lambda t: t[0])
        vals = [p for p, _ in pace_vals]
        q1 = float(np.quantile(vals, 0.25))
        q2 = float(np.quantile(vals, 0.50))
        q3 = float(np.quantile(vals, 0.75))
        quart_defs = [
            ("pace Q1 (slow)", lambda p: p <= q1),
            ("pace Q2", lambda p: q1 < p <= q2),
            ("pace Q3", lambda p: q2 < p <= q3),
            ("pace Q4 (fast)", lambda p: p > q3),
        ]
        for label, pred in quart_defs:
            rs = [r for p, r in pace_vals if pred(p)]
            m = slice_metrics(rs)
            m["label"] = label
            m["red_zone"] = red_zone(m)
            pace_slices.append(m)

    return {
        "overall": base,
        "confidence": confidence,
        "spread_buckets": spread_buckets,
        "favorite_vs_underdog": fav_ud,
        "pace_quartiles": pace_slices,
        "notes": [
            "Slices computed on selected bets (post exposure controls).",
            "Pace quartiles only appear if pace_game is present (typically diagnostic-only in this repo).",
        ],
    }


def build_failure_analysis(selected_bets: List[Any]) -> dict[str, Any]:
    losses = [r for r in selected_bets if (getattr(r, "pnl_units", None) is not None and float(getattr(r, "pnl_units") or 0.0) < 0)]
    worst = sorted(losses, key=lambda r: float(getattr(r, "pnl_units") or 0.0))[:10]
    worst_rows = [
        {
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
        for r in worst
    ]

    overconf = [r for r in selected_bets if getattr(r, "outcome", None) == "loss" and getattr(r, "model_prob", None) is not None]
    overconf = sorted(overconf, key=lambda r: -(float(getattr(r, "model_prob") or 0.0)))[:10]
    overconf_rows = [
        {
            "game_id": getattr(r, "game_id", None),
            "date": (getattr(r, "meta", {}) or {}).get("game_date"),
            "side": getattr(r, "side", None),
            "model_prob": getattr(r, "model_prob", None),
            "implied_prob": getattr(r, "implied_prob", None),
            "edge": getattr(r, "edge_vs_implied", None),
            "pnl_units": getattr(r, "pnl_units", None),
        }
        for r in overconf
    ]

    edges = [getattr(r, "edge_vs_implied", None) for r in selected_bets if getattr(r, "edge_vs_implied", None) is not None]
    edge_buckets = []
    if edges:
        defs = [
            ("edge<0", lambda e: e < 0),
            ("0-1%", lambda e: 0 <= e < 0.01),
            ("1-2%", lambda e: 0.01 <= e < 0.02),
            ("2-4%", lambda e: 0.02 <= e < 0.04),
            ("4%+", lambda e: e >= 0.04),
        ]
        for label, pred in defs:
            rs = [r for r in selected_bets if getattr(r, "edge_vs_implied", None) is not None and pred(float(getattr(r, "edge_vs_implied")))]
            m = slice_metrics(rs)
            m["label"] = label
            edge_buckets.append(m)

    return {
        "largest_losses": worst_rows,
        "overconfident_losses": overconf_rows,
        "edge_decay": edge_buckets,
        "notes": [
            "Largest losses are historical single-bet PnL under the selected odds assumption (artifact).",
            "Overconfident losses highlight calibration failures (high model_prob, negative outcome).",
        ],
    }


