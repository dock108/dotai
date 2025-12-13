from __future__ import annotations

from typing import Any, Dict, List


def mc_assumptions_payload(target_def: Dict[str, Any], exposure: Dict[str, Any] | None) -> Dict[str, Any]:
    return {
        "bet_sizing": "1 unit flat risk (historical simulation artifact)",
        "kelly": "not used",
        "odds_assumption": target_def.get("odds_assumption"),
        "independence_assumption": True,
        "selection_policy": (exposure or {}).get("notes", []),
    }


def mc_interpretation_lines(mc_summary: Dict[str, Any] | None, exposure: Dict[str, Any] | None) -> List[str]:
    if not mc_summary or not mc_summary.get("runs"):
        return ["No MC runs available."]
    mean_pnl = float(mc_summary.get("mean_pnl") or 0.0)
    p5 = float(mc_summary.get("p5_pnl") or 0.0)
    p95 = float(mc_summary.get("p95_pnl") or 0.0)
    actual = float(mc_summary.get("actual_pnl") or 0.0)
    luck = float(mc_summary.get("luck_score") or 0.0)
    span = p95 - p5
    lines: List[str] = []
    lines.append("MC is decision-support: it’s a distribution over outcomes, not a promise.")
    lines.append(f"Variance range (P5→P95) spans {span:.1f} units over this bet set; wider spans mean variance dominates.")
    if abs(mean_pnl) < 1e-6:
        lines.append("Median/mean are near 0 under the MC baseline — edges may be fragile.")
    if abs(luck) > max(3.0, 0.25 * max(1.0, abs(span))):
        lines.append("Luck score is large vs the MC baseline — be cautious attributing results to skill.")
    lines.append(f"Luck score = actual ({actual:.1f}) − expected mean ({mean_pnl:.1f}) = {luck:.1f}.")
    if exposure and exposure.get("warnings"):
        lines.append("Exposure warnings apply: selection/caps can create over-betting artifacts.")
    return lines


