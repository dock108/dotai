"""Guardrails specific to sports highlight playlist requests."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas.theory import Domain


@dataclass(slots=True)
class SportsGuardrailResult:
    """Represents a triggered sports highlight guardrail."""

    code: str
    description: str
    severity: str = "soft"  # "hard" (block) or "soft" (flag)


# Hard block keywords - immediate reject
COPYRIGHT_VIOLATION_KEYWORDS: tuple[str, ...] = (
    "full game reupload",
    "reupload full game",
    "pirated game",
    "stolen broadcast",
    "illegal stream",
    "bootleg",
    "unauthorized broadcast",
    "copyrighted full game",
    "ppv reupload",
    "pay per view reupload",
    "ppv stream",
    "full ppv",
    "download full game",
    "download broadcast",
    "save full game",
    "pirate the whole broadcast",
    "pirate broadcast",
    "bypass youtube",
    "download from youtube",
    "youtube downloader",
    "rip from youtube",
    "extract from youtube",
)

NSFW_VIOLENT_KEYWORDS: tuple[str, ...] = (
    "violence",
    "fight",
    "brawl",
    "assault",
    "injury compilation",
    "worst injuries",
    "brutal hits",
    "dirty plays compilation",
    "cheap shots",
    "unsportsmanlike",
    "nsfw",
    "explicit",
    "adult content",
)

# Soft flag keywords - allowed but flagged
SKETCHY_CONTENT_KEYWORDS: tuple[str, ...] = (
    "leaked",
    "unauthorized",
    "not official",
    "fan upload",
    "recorded from tv",
    "tv recording",
    "screen recording",
)


def check_sports_highlight_guardrails(text: str, domain: Domain | None = None) -> list[SportsGuardrailResult]:
    """Check sports highlight-specific guardrails.
    
    Blocks:
    - Copyright violations (full game reuploads, PPV reuploads)
    - NSFW/violent content unrelated to sports
    
    Flags:
    - Sketchy content (leaked, unauthorized, fan uploads)
    
    Args:
        text: User request text
        domain: Request domain (should be playlist or None)
    
    Returns:
        List of guardrail results
    """
    results: list[SportsGuardrailResult] = []
    text_lower = text.lower()
    
    # Hard blocks - copyright violations and YouTube bypass attempts
    for keyword in COPYRIGHT_VIOLATION_KEYWORDS:
        if keyword in text_lower:
            # Check if it's a "pirate the whole broadcast" type request
            if any(term in text_lower for term in ["pirate", "download", "bypass", "rip", "extract"]):
                description = (
                    "This request appears to seek unauthorized downloads or attempts to bypass YouTube's platform. "
                    "We can only provide links to official YouTube videos. "
                    "Would you like a highlight-style playlist instead?"
                )
            else:
                description = "This request appears to seek copyrighted full game reuploads or PPV content, which we cannot provide."
            
            results.append(
                SportsGuardrailResult(
                    code="hard:copyright-violation",
                    description=description,
                    severity="hard",
                )
            )
            break  # Only flag once
    
    # Hard blocks - NSFW/violent content
    for keyword in NSFW_VIOLENT_KEYWORDS:
        if keyword in text_lower:
            results.append(
                SportsGuardrailResult(
                    code="hard:nsfw-violent",
                    description="This request appears to seek NSFW or violent content unrelated to sports highlights, which we cannot provide.",
                    severity="hard",
                )
            )
            break
    
    # Soft flags - sketchy content
    for keyword in SKETCHY_CONTENT_KEYWORDS:
        if keyword in text_lower:
            results.append(
                SportsGuardrailResult(
                    code="soft:sketchy-content",
                    description="This request may seek unauthorized or unofficial content. We only return official YouTube videos.",
                    severity="soft",
                )
            )
            break
    
    return results


def has_hard_block_sports(results: list[SportsGuardrailResult]) -> bool:
    """Check if any hard blocks are present.
    
    Args:
        results: List of guardrail results
    
    Returns:
        True if any hard block is present
    """
    return any(result.severity == "hard" for result in results)


def summarize_sports_guardrails(results: list[SportsGuardrailResult]) -> list[str]:
    """Summarize guardrail results as flag strings.
    
    Args:
        results: List of guardrail results
    
    Returns:
        List of flag strings for API response
    """
    return [result.code for result in results]


def normalize_sports_request(text: str) -> str:
    """Normalize sports highlight request text.
    
    - Lowercase
    - Remove URLs
    - Strip extra whitespace
    
    Args:
        text: Raw user input
    
    Returns:
        Normalized text
    """
    # Remove URLs
    url_pattern = re.compile(r"https?://\S+|www\.\S+")
    text = url_pattern.sub("", text)
    
    # Lowercase and strip
    text = text.lower().strip()
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    
    return text

