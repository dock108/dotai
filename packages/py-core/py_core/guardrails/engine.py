"""Guardrail engine with input normalization, hard blocks, and soft flags."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from ..schemas.theory import Domain


@dataclass(slots=True)
class GuardrailResult:
    """Represents a triggered guardrail."""

    code: str
    description: str
    severity: str = "soft"  # "hard" (block) or "soft" (flag)


@dataclass(slots=True)
class NormalizedInput:
    """Normalized input after processing."""

    text: str
    entities: dict[str, list[str]]  # people, tickers, dates
    urls_removed: list[str]


# Hard block categories - immediate reject
INSIDER_TRADING_KEYWORDS: tuple[str, ...] = (
    "insider",
    "i know someone at",
    "non public",
    "earnings leak",
    "material non-public",
    "inside information",
    "confidential information",
)

TAX_EVASION_KEYWORDS: tuple[str, ...] = (
    "avoid taxes",
    "illegal",
    "hide from irs",
    "wash trades to avoid",
    "tax evasion",
    "tax fraud",
    "offshore to avoid",
)

GUARANTEED_WINNINGS_KEYWORDS: tuple[str, ...] = (
    "guaranteed winner",
    "sure thing",
    "risk free guaranteed",
    "can't lose",
    "guaranteed profit",
    "100% win",
    "cannot lose",
    "guaranteed return",
)

VIOLENCE_HATE_KEYWORDS: tuple[str, ...] = (
    "kill",
    "murder",
    "harm",
    "violence",
    "attack",
    "hate",
    "threat",
)

# Soft flags - allowed but labeled
ABSOLUTE_LANGUAGE: tuple[str, ...] = (
    "always",
    "never",
    "everyone knows",
    "everyone",
    "nobody",
    "impossible",
    "certain",
    "definitely",
    "absolutely",
)

WEAK_CLAIM_PATTERNS: tuple[str, ...] = (
    "i just feel like",
    "i think maybe",
    "probably",
    "might be",
    "could be",
    "seems like",
)

SOCIAL_MEDIA_PATTERNS: tuple[str, ...] = (
    "thread:",
    "🧵",
    "1/",
    "2/",
    "3/",
    "breaking:",
    "hot take:",
)


def normalize_input(text: str) -> NormalizedInput:
    """Normalize input: lowercase, strip URLs, extract entities."""
    normalized = text.lower().strip()
    
    # Extract and remove URLs
    url_pattern = r"https?://[^\s]+"
    urls = re.findall(url_pattern, normalized)
    normalized = re.sub(url_pattern, "", normalized)
    
    # Extract tickers (e.g., $BTC, $AAPL, BTC, AAPL)
    ticker_pattern = r"\$?[A-Z]{2,5}\b"
    tickers = re.findall(ticker_pattern, text.upper())
    
    # Extract dates (simple patterns)
    date_pattern = r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}"
    dates = re.findall(date_pattern, normalized)
    
    # Extract people (capitalized words, simple heuristic)
    people_pattern = r"\b[A-Z][a-z]+ [A-Z][a-z]+\b"
    people = re.findall(people_pattern, text)
    
    entities = {
        "tickers": list(set(tickers)),
        "dates": list(set(dates)),
        "people": list(set(people)),
    }
    
    return NormalizedInput(
        text=normalized,
        entities=entities,
        urls_removed=urls,
    )


def check_hard_blocks(normalized: NormalizedInput, domain: Domain | None = None) -> list[GuardrailResult]:
    """Check for hard block categories - immediate reject."""
    results: list[GuardrailResult] = []
    text = normalized.text
    
    # Insider trading
    for keyword in INSIDER_TRADING_KEYWORDS:
        if keyword in text:
            results.append(
                GuardrailResult(
                    code="hard:insider-trading",
                    description="This theory references insider trading or material non-public information, which we cannot evaluate.",
                    severity="hard",
                )
            )
            break
    
    # Tax evasion (crypto/stocks domains)
    if domain in (Domain.crypto, Domain.stocks):
        for keyword in TAX_EVASION_KEYWORDS:
            if keyword in text:
                results.append(
                    GuardrailResult(
                        code="hard:tax-evasion",
                        description="This theory involves tax evasion or illegal tax avoidance, which we cannot evaluate.",
                        severity="hard",
                    )
                )
                break
    
    # Guaranteed winnings
    for keyword in GUARANTEED_WINNINGS_KEYWORDS:
        if keyword in text:
            results.append(
                GuardrailResult(
                    code="hard:guaranteed-winnings",
                    description="No investment or bet can be guaranteed. This theory makes impossible claims.",
                    severity="hard",
                )
            )
            break
    
    # Violence/hate
    for keyword in VIOLENCE_HATE_KEYWORDS:
        if keyword in text:
            results.append(
                GuardrailResult(
                    code="hard:violence-hate",
                    description="This theory contains language we cannot process. Please reframe your question.",
                    severity="hard",
                )
            )
            break
    
    # Recent deaths check (conspiracy domain) - placeholder
    if domain == Domain.conspiracies:
        # TODO: Check against news/wiki API for recent deaths
        # For now, check for common patterns
        if "died" in text or "death" in text:
            # This would need actual API call to verify
            pass
    
    return results


def check_soft_flags(normalized: NormalizedInput) -> list[GuardrailResult]:
    """Check for soft flags - allowed but labeled."""
    results: list[GuardrailResult] = []
    text = normalized.text
    
    # Absolute language
    absolute_count = sum(1 for word in ABSOLUTE_LANGUAGE if word in text)
    if absolute_count >= 2:
        results.append(
            GuardrailResult(
                code="soft:absolute-language",
                description="Your theory uses absolute language that rarely matches real-world data.",
                severity="soft",
            )
        )
    
    # Weak claim structure
    if any(pattern in text for pattern in WEAK_CLAIM_PATTERNS):
        results.append(
            GuardrailResult(
                code="soft:weak-claim",
                description="This theory uses uncertain language. Consider strengthening your hypothesis.",
                severity="soft",
            )
        )
    
    # Social media patterns
    if any(pattern in text for pattern in SOCIAL_MEDIA_PATTERNS):
        results.append(
            GuardrailResult(
                code="soft:social-media",
                description="This appears to be copied from social media. We treated it as untrusted and checked it against real data.",
                severity="soft",
            )
        )
    
    return results


def evaluate_guardrails(text: str, domain: Domain | None = None) -> list[GuardrailResult]:
    """Evaluate guardrails with normalization, hard blocks, and soft flags."""
    normalized = normalize_input(text)
    results: list[GuardrailResult] = []
    
    # Check hard blocks first (these will block the request)
    hard_blocks = check_hard_blocks(normalized, domain)
    results.extend(hard_blocks)
    
    # If hard blocks found, return early (don't check soft flags)
    if hard_blocks:
        return results
    
    # Check soft flags
    soft_flags = check_soft_flags(normalized)
    results.extend(soft_flags)
    
    return results


def has_hard_block(results: list[GuardrailResult]) -> bool:
    """Check if any hard blocks were triggered."""
    return any(r.severity == "hard" for r in results)


def summarize_guardrails(results: Iterable[GuardrailResult]) -> list[str]:
    """Helper to turn guardrail objects into serializable strings."""
    return [f"{result.code} ({result.description})" for result in results]

