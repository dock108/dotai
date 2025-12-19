from __future__ import annotations

"""
Theory registry for dynamic loading, A/B testing, and versioning.

Usage:

@register_theory("closing_line_underdog", version="v1")
class ClosingLineUnderdog(MicroModel):
    ...
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from engine.common.micro_model import MicroModel


@dataclass
class TheoryEntry:
    name: str
    cls: Type[MicroModel]
    version: str = "v1"
    enabled: bool = True
    tags: Optional[List[str]] = None
    description: Optional[str] = None


_THEORY_REGISTRY: Dict[str, TheoryEntry] = {}


def register_theory(
    name: str,
    *,
    version: str = "v1",
    enabled: bool = True,
    tags: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> Callable[[Type[MicroModel]], Type[MicroModel]]:
    """
    Decorator to register a MicroModel for dynamic discovery.

    Supports basic enable/disable and simple version tagging for A/B testing or upgrades.
    """

    def decorator(cls: Type[MicroModel]) -> Type[MicroModel]:
        if not issubclass(cls, MicroModel):
            raise TypeError("register_theory can only be applied to MicroModel subclasses")
        _THEORY_REGISTRY[name] = TheoryEntry(
            name=name,
            cls=cls,
            version=version,
            enabled=enabled,
            tags=tags or [],
            description=description,
        )
        return cls

    return decorator


def get_theory(name: str) -> TheoryEntry | None:
    return _THEORY_REGISTRY.get(name)


def list_theories(enabled_only: bool = False) -> Dict[str, TheoryEntry]:
    if not enabled_only:
        return dict(_THEORY_REGISTRY)
    return {k: v for k, v in _THEORY_REGISTRY.items() if v.enabled}


def enable_theory(name: str, enabled: bool = True) -> None:
    entry = _THEORY_REGISTRY.get(name)
    if entry:
        entry.enabled = enabled


def create_theory(name: str, **kwargs: Any) -> MicroModel:
    entry = _THEORY_REGISTRY.get(name)
    if not entry:
        raise KeyError(f"Theory '{name}' is not registered")
    return entry.cls(**kwargs)




