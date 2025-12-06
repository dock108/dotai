from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping


class MicroModel(ABC):
    """
    Base class for micro-models across sports.

    Implementations should be pure/side-effect free and reusable in backtests or live flows.
    """

    @abstractmethod
    def should_trigger(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> bool:
        """Return True if this model wants to evaluate given the event/features."""
        raise NotImplementedError

    @abstractmethod
    def compute_ev(self, event: Mapping[str, Any], features: Mapping[str, Any]) -> float | None:
        """Return expected value for the target market, or None if not computable."""
        raise NotImplementedError

    @abstractmethod
    def compute_outcome(self, result_data: Mapping[str, Any]) -> Dict[str, Any]:
        """Compute realized outcome metrics (e.g., win/loss/push, pnl)."""
        raise NotImplementedError

    @abstractmethod
    def generate_output_row(
        self,
        event: Mapping[str, Any],
        features: Mapping[str, Any],
        ev: float | None,
        outcome: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        """Render a standard result row for backtests/live signals."""
        raise NotImplementedError


