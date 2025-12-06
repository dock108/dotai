from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Mapping, Tuple


class FeatureBuilder(ABC):
    """
    Base wrapper to build feature sets.

    Supports minimal vs full modes; subclasses implement domain-specific extraction.
    """

    def __init__(self, mode: str = "minimal"):
        if mode not in {"minimal", "full"}:
            raise ValueError("mode must be 'minimal' or 'full'")
        self.mode = mode

    @abstractmethod
    def required_fields(self) -> Iterable[str]:
        """Fields needed from the event/raw record to build minimal features."""
        raise NotImplementedError

    @abstractmethod
    def build_minimal(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        """Build minimal feature dict (e.g., closing odds + result)."""
        raise NotImplementedError

    @abstractmethod
    def build_full(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        """Build full feature dict (adds stats/rolling/situational/etc.)."""
        raise NotImplementedError

    def build(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        if self.mode == "minimal":
            return self.build_minimal(event)
        return self.build_full(event)

    def with_mode(self, mode: str) -> "FeatureBuilder":
        return self.__class__(mode=mode)


