from __future__ import annotations

"""
Parallel micro-model evaluation helper.
"""

import asyncio
from typing import Any, Iterable, Mapping, Sequence

from engine.common.micro_model import MicroModel


async def evaluate_models(
    models: Sequence[MicroModel],
    events: Iterable[Mapping[str, Any]],
    features_by_event: Mapping[Any, Mapping[str, Any]],
) -> list[dict]:
    """
    Evaluate multiple micro-models over a set of events in parallel (best-effort).
    """

    async def eval_one(model: MicroModel, event: Mapping[str, Any]):
        feats = features_by_event.get(event.get("game_id"), {}) if features_by_event else {}
        if not model.should_trigger(event, feats):
            return None
        ev = model.compute_ev(event, feats)
        outcome = model.compute_outcome(event.get("metrics", {}))
        return model.generate_output_row(event, feats, outcome=outcome, ev=ev)

    tasks = []
    for event in events:
        for model in models:
            tasks.append(eval_one(model, event))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if r and not isinstance(r, Exception)]




