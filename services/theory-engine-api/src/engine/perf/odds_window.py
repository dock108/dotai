from __future__ import annotations

"""
Preloaded odds window placeholder for fast lookups.
"""

from typing import Any, Dict, Iterable, Mapping


def preload_odds_window(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """
    Ingest odds rows (e.g., recent window) into a dict for quick access.
    """
    window: Dict[str, Any] = {}
    for row in rows:
        game_id = str(row.get("game_id"))
        if not game_id:
            continue
        window.setdefault(game_id, []).append(row)
    return window



