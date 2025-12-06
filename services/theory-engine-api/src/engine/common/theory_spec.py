from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class TheoryCondition(BaseModel):
    """A single condition that must hold to trigger a theory (domain-agnostic)."""

    key: str
    op: str
    value: Any


class TheorySignal(BaseModel):
    """Signal to emit when a theory triggers (domain-agnostic)."""

    name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class TheorySpec(BaseModel):
    """
    Universal theory specification.

    Applies to all sports; downstream micro-models interpret the fields.
    """

    conditions: List[TheoryCondition] = Field(default_factory=list)
    signals: List[TheorySignal] = Field(default_factory=list)
    target_market: str
    params: Dict[str, Any] = Field(default_factory=dict)

    @validator("target_market")
    def _non_empty_market(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("target_market must be non-empty")
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


