"""Minimal guardrail engine placeholder.

The real implementation will host prompt filters, tier gates, and risk scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..schemas.theory import Domain


@dataclass(slots=True)
class GuardrailResult:
    """Represents a triggered guardrail."""

    code: str
    description: str


SENSITIVE_KEYWORDS: tuple[str, ...] = ("insider", "fix the game", "pump and dump", "mkultra")


def evaluate_guardrails(text: str, domain: Domain | None = None) -> list[GuardrailResult]:
    """Very lightweight heuristics to bootstrap the pipeline."""

    lowered = text.lower()
    results: list[GuardrailResult] = []

    for keyword in SENSITIVE_KEYWORDS:
        if keyword in lowered:
            results.append(
                GuardrailResult(
                    code="keyword:sensitive",
                    description=f"Contains high-risk term '{keyword}'.",
                )
            )

    if domain == Domain.bets and "sure thing" in lowered:
        results.append(
            GuardrailResult(
                code="bets:sure-thing",
                description="Sports betting claims cannot guarantee outcomes.",
            )
        )

    return results


def summarize_guardrails(results: Iterable[GuardrailResult]) -> list[str]:
    """Helper to turn guardrail objects into serializable strings."""

    return [f"{result.code} ({result.description})" for result in results]

