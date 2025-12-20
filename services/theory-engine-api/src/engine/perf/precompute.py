from __future__ import annotations

"""
Precompute daily game features (placeholder job hook).
"""

from typing import Any, Iterable, Mapping, Callable


async def precompute_features(
    game_ids: Iterable[int],
    build_fn: Callable[[int], Mapping[str, Any]],
    persist_fn: Callable[[int, Mapping[str, Any]], None],
) -> None:
    for gid in game_ids:
        features = build_fn(gid)
        await persist_fn(gid, features)





