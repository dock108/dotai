from __future__ import annotations

from typing import Any, Dict, Mapping


def safe_diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a - b


def safe_sum(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a + b


def coalesce_stats(source: Mapping[str, Any] | None, keys: tuple[str, ...]) -> dict:
    src = source or {}
    return {k: src.get(k) for k in keys if k in src}





