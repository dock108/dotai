"""Conspiracies domain router with Wikipedia and fact-check sources."""

from __future__ import annotations

import json
import os
from datetime import datetime

from ..utils import now_utc
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

from py_core import (
    Domain,
    TheoryRequest,
    TheoryResponse,
    DataSource,
    evaluate_guardrails,
    has_hard_block,
    summarize_guardrails,
)
from py_core.data.fetchers import ContextResult, fetch_conspiracy_context
from py_core.scoring.metrics import compute_domain_verdict
from ..logging_config import get_logger

router = APIRouter(prefix="/api/theory", tags=["conspiracies"])
logger = get_logger(__name__)
PROMPT_PATH = Path(__file__).resolve().parent.parent / "ai_prompts" / "conspiracy_narrative.md"


class ClaimEvidence(BaseModel):
    claim: str = Field(description="Believer argument in plain language")
    evidence: str = Field(description="Best available counter-evidence")
    verdict: str = Field(description="supported|debunked|unclear")


class ConspiraciesResponse(TheoryResponse):
    """Conspiracies-specific response with narrative storytelling."""

    claim_text: str = Field(description="Claim rewritten cleanly in plain English")
    story_sections: list[str] = Field(
        default_factory=list, description="Narrative paragraphs explaining the conspiracy story"
    )
    claims_vs_evidence: list[ClaimEvidence] = Field(
        default_factory=list, description="Side-by-side comparison of major claims and counter-evidence"
    )
    verdict_text: str = Field(description="Narrative verdict sentence with context")
    confidence_score: int = Field(description="Final 0-100 score derived from rubric weighting")
    sources_used: list[str] = Field(default_factory=list, description="Human-friendly list of sources used")
    fuels_today: list[str] = Field(default_factory=list, description="Why the theory still circulates today")


CONFIDENCE_WEIGHTS: dict[str, float] = {
    "historical_documentation": 0.30,
    "independent_corroboration": 0.20,
    "scientific_plausibility": 0.20,
    "expert_consensus": 0.20,
    "internal_coherence": 0.10,
}


def _load_conspiracy_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return """You are a neutral historian and investigative analyst. Explain the story behind the user's conspiracy theory in five sections:
1. Claim
2. The Story Behind the Theory (4-7 paragraphs)
3. Claims vs Evidence (bulleted comparison)
4. Verdict & Confidence (0-100) using the fixed rubric
5. Sources Used

Respond with strict JSON following the documented schema."""


def _sanitize_json_response(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def _build_context_prompt(user_text: str, wikipedia_data: dict[str, Any], factcheck_data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("USER_QUERY:")
    lines.append(user_text.strip())
    lines.append("")

    if wikipedia_data:
        summary = wikipedia_data.get("summary")
        if summary:
            lines.append("WIKIPEDIA_SUMMARY:")
            lines.append(summary.strip())
            lines.append("")
        key_facts = wikipedia_data.get("key_facts") or []
        if key_facts:
            lines.append("KEY_FACTS:")
            for fact in key_facts[:10]:
                lines.append(f"- {fact}")
            lines.append("")
        if wikipedia_data.get("url"):
            lines.append(f"WIKIPEDIA_URL: {wikipedia_data['url']}")
            lines.append("")
    else:
        lines.append("WIKIPEDIA_SUMMARY: Not available")
        lines.append("")

    claims = factcheck_data.get("claims") if factcheck_data else None
    if claims:
        lines.append("FACT_CHECK_CLAIMS:")
        for claim in claims[:8]:
            rating = claim.get("rating", "Unknown").title()
            publisher = claim.get("publisher", "Unknown source")
            text = claim.get("text", "").strip()
            lines.append(f"- Claim: {text} | Rating: {rating} | Source: {publisher}")
    else:
        lines.append("FACT_CHECK_CLAIMS: None found")

    return "\n".join(lines).strip()


def _confidence_label(score: int) -> str:
    if score <= 20:
        return "Very Low Confidence"
    if score <= 40:
        return "Low Confidence"
    if score <= 60:
        return "Mixed Confidence"
    if score <= 80:
        return "Moderate Confidence"
    return "High Confidence"


def _context_sources(wikipedia_data: dict[str, Any], factcheck_data: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    if wikipedia_data:
        title = wikipedia_data.get("title")
        if title:
            sources.append(f"Wikipedia — {title}")
        else:
            sources.append("Wikipedia (timeline + citations)")
    if factcheck_data and factcheck_data.get("claims"):
        publishers = {
            claim.get("publisher", "Fact-check database")
            for claim in factcheck_data["claims"]
            if claim.get("publisher")
        }
        if publishers:
            sources.append("Fact-check sources: " + ", ".join(sorted(publishers)))
        else:
            sources.append("Fact-check databases")
    return sources


def analyze_conspiracy_theory(
    text: str, context: ContextResult, raw_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Generate a narrative analysis, falling back to heuristic mode if needed."""

    raw_data = raw_data or {}
    wikipedia_data = raw_data.get("wikipedia_data", {}) or {}
    factcheck_data = raw_data.get("factcheck_data", {}) or {}

    try:
        return _generate_narrative_analysis(text, context, wikipedia_data, factcheck_data)
    except Exception as exc:
        logger.warning("conspiracy_narrative_generation_failed", exc_info=True)
        return _heuristic_analysis(text, context, wikipedia_data, factcheck_data)


def _generate_narrative_analysis(
    text: str,
    context: ContextResult,
    wikipedia_data: dict[str, Any],
    factcheck_data: dict[str, Any],
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable required for narrative generation")

    client = OpenAI(api_key=api_key)
    system_prompt = _load_conspiracy_prompt()
    user_prompt = _build_context_prompt(text, wikipedia_data, factcheck_data)

    model = os.getenv("CONSPIRACY_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=1400,
    )

    content = response.choices[0].message.content or ""
    payload = json.loads(_sanitize_json_response(content))

    story_sections = payload.get("story_sections") or []
    if isinstance(story_sections, str):
        story_sections = [para.strip() for para in story_sections.split("\n") if para.strip()]

    if not story_sections:
        summary = wikipedia_data.get("summary")
        if summary:
            story_sections = [summary]
        else:
            story_sections = ["No narrative context available from mainstream sources."]

    claims_vs_evidence_payload = payload.get("claims_vs_evidence") or []
    claims_vs_evidence: list[ClaimEvidence] = []
    for item in claims_vs_evidence_payload:
        claim = (item.get("claim") or "").strip()
        evidence = (item.get("evidence") or "").strip()
        verdict = (item.get("verdict") or "unclear").strip()
        if claim and evidence:
            claims_vs_evidence.append(ClaimEvidence(claim=claim, evidence=evidence, verdict=verdict))

    breakdown_input = payload.get("confidence_breakdown") or {}
    breakdown: dict[str, dict[str, Any]] = {}
    weighted_score = 0.0
    for metric, weight in CONFIDENCE_WEIGHTS.items():
        node = breakdown_input.get(metric) or {}
        score = int(max(0, min(100, int(node.get("score", 0)))))
        reason = (node.get("reason") or "Reason not provided.").strip()
        breakdown[metric] = {"score": score, "reason": reason}
        weighted_score += score * weight

    confidence_score = int(round(max(0, min(100, weighted_score))))
    verdict_text = payload.get("verdict_text")
    if not verdict_text:
        verdict_label = _confidence_label(confidence_score)
        verdict_text = f"{verdict_label} ({confidence_score}/100)"

    sources_used = payload.get("sources_used") or []
    if isinstance(sources_used, str):
        sources_used = [sources_used]
    if not sources_used:
        sources_used = _context_sources(wikipedia_data, factcheck_data)

    fuels_today = payload.get("fuels_today") or payload.get("what_fuels_it_today") or []
    if isinstance(fuels_today, str):
        fuels_today = [fuels_today]

    return {
        "claim_text": payload.get("claim") or text.strip(),
        "story_sections": story_sections,
        "claims_vs_evidence": claims_vs_evidence,
        "verdict_text": verdict_text,
        "confidence_score": confidence_score,
        "confidence_breakdown": breakdown,
        "sources_used": sources_used,
        "fuels_today": fuels_today,
        "raw_context_sources": _context_sources(wikipedia_data, factcheck_data),
        "limitations": context.limitations or [],
    }


def _heuristic_analysis(
    text: str,
    context: ContextResult,
    wikipedia_data: dict[str, Any],
    factcheck_data: dict[str, Any],
) -> dict[str, Any]:
    """Fallback analysis when the narrative engine is unavailable."""
    import re

    text_lower = text.lower()
    summary = wikipedia_data.get("summary") or ""
    sentences = [s.strip() for s in summary.split(". ") if s.strip()]

    key_facts: list[str] = []
    if wikipedia_data.get("key_facts"):
        key_facts.extend(wikipedia_data["key_facts"][:8])
    elif sentences:
        key_facts.extend(sentences[:8])

    evidence_against: list[str] = []
    evidence_for: list[str] = []

    contradict_keywords = [
        "contradict",
        "dispute",
        "debunk",
        "false",
        "untrue",
        "misleading",
        "refute",
        "reject",
        "evidence shows",
        "scientific",
        "verified",
        "confirmed",
        "proven",
        "established",
        "documented",
        "recorded",
    ]

    for sentence in sentences:
        lower = sentence.lower()
        if any(keyword in lower for keyword in contradict_keywords):
            evidence_against.append(sentence[:300])

    if not evidence_against and sentences:
        evidence_against.extend(sentences[:3])

    support_keywords = ["evidence suggests", "indicates", "supports", "consistent with", "according to", "alleged"]
    for sentence in sentences:
        lower = sentence.lower()
        if any(keyword in lower for keyword in support_keywords):
            evidence_for.append(sentence[:300])

    fact_check_ratings: list[str] = []
    if factcheck_data.get("claims"):
        for claim in factcheck_data["claims"]:
            rating = claim.get("rating", "").lower()
            fact_check_ratings.append(rating)
            publisher = claim.get("publisher", "Fact-check source")
            text_snippet = claim.get("text", "")
            if "false" in rating or "misleading" in rating:
                evidence_against.append(f"{publisher} fact-check ({rating}): {text_snippet[:200]}")
            elif "true" in rating or "correct" in rating:
                evidence_for.append(f"{publisher} fact-check ({rating}): {text_snippet[:200]}")

    assumptions: list[str] = []
    assumption_patterns = [
        r"assume[sd]?\s+that",
        r"presume[sd]?\s+that",
        r"suppose[sd]?\s+that",
        r"if\s+(?:we|they|it)\s+(?:assume|presume|suppose)",
        r"without\s+evidence",
        r"no\s+proof",
        r"unproven",
    ]

    for pattern in assumption_patterns:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 100)
            snippet = text[start:end].strip()
            if snippet and snippet not in assumptions:
                assumptions.append(snippet[:200])

    base_score = 50
    if fact_check_ratings:
        false_count = sum(1 for r in fact_check_ratings if "false" in r or "misleading" in r)
        true_count = sum(1 for r in fact_check_ratings if "true" in r or "correct" in r)
        base_score += 20 * min(true_count, 2)
        base_score -= 30 * min(false_count, 2)

    if len(evidence_against) > len(evidence_for) * 1.5:
        base_score -= 15
    elif len(evidence_for) > len(evidence_against) * 1.5:
        base_score += 10

    base_score -= 5 * min(len(assumptions), 3)
    confidence_score = max(0, min(100, int(base_score)))

    claims_vs_evidence: list[ClaimEvidence] = []
    for idx, ev in enumerate(evidence_against[:3]):
        claims_vs_evidence.append(
            ClaimEvidence(
                claim=f"Popular argument #{idx + 1}",
                evidence=ev,
                verdict="debunked",
            )
        )

    for support in evidence_for[:2]:
        claims_vs_evidence.append(
            ClaimEvidence(
                claim="Talking point believers cite",
                evidence=support,
                verdict="supported",
            )
        )

    if not claims_vs_evidence and key_facts:
        claims_vs_evidence.append(
            ClaimEvidence(
                claim="General belief",
                evidence=key_facts[0],
                verdict="unclear",
            )
        )

    breakdown = {
        metric: {
            "score": confidence_score,
            "reason": "Estimated via heuristic analysis (fallback mode).",
        }
        for metric in CONFIDENCE_WEIGHTS.keys()
    }

    verdict_label = _confidence_label(confidence_score)
    story_sections = []
    if key_facts:
        story_sections.append(" ".join(key_facts[:3]))
    elif summary:
        story_sections.append(summary)
    else:
        story_sections.append("No mainstream documentation available; only limited context provided.")

    fuels_today = assumptions[:3]

    return {
        "claim_text": text.strip(),
        "story_sections": story_sections,
        "claims_vs_evidence": claims_vs_evidence,
        "verdict_text": f"{verdict_label} ({confidence_score}/100) — fallback narrative",
        "confidence_score": confidence_score,
        "confidence_breakdown": breakdown,
        "sources_used": _context_sources(wikipedia_data, factcheck_data),
        "fuels_today": fuels_today,
        "raw_context_sources": _context_sources(wikipedia_data, factcheck_data),
        "limitations": context.limitations or [],
    }




@router.post("/conspiracies", response_model=ConspiraciesResponse)
async def evaluate_conspiracy_theory(req: TheoryRequest) -> ConspiraciesResponse:
    """Evaluate a conspiracy theory with strict guardrails and fact-checking."""
    
    # Run guardrails (extra strict for conspiracies)
    guardrail_results = evaluate_guardrails(req.text, Domain.conspiracies)
    if has_hard_block(guardrail_results):
        raise HTTPException(
            status_code=400,
            detail="This theory cannot be evaluated due to guardrail restrictions.",
        )
    
    guardrail_flags = summarize_guardrails(guardrail_results)
    
    # Fetch conspiracy context (Wikipedia, fact-check sites)
    from py_core.data.cache import CacheKey
    from py_core.data.fetchers import _get_cache
    
    context = fetch_conspiracy_context(req.text, limit=5, sources=["wikipedia", "fact-check-db"])
    
    # Get raw data from cache for detailed analysis
    cache = _get_cache()
    cache_key = CacheKey(
        context_type="conspiracy",
        query=req.text,
        filters={"limit": 5, "sources": ["wikipedia", "fact-check-db"]},
    )
    cached_entry = cache.get(cache_key)
    raw_data: dict[str, Any] = {}
    if cached_entry:
        raw_data = cached_entry.payload
    
    # Analyze theory with context and raw data
    analysis = analyze_conspiracy_theory(req.text, context, raw_data)
    
    # Get base verdict
    verdict_bundle = compute_domain_verdict(Domain.conspiracies, req.text)
    
    # Build data_used list from context
    data_used: list[DataSource] = []
    if context.data_source_name:
        data_used.append(
            DataSource(
                name=context.data_source_name,
                cache_status=context.cache_status,
                details=context.data_source_details,
            )
        )
    else:
        data_used.append(
            DataSource(
                name="Wikipedia",
                cache_status="cached",
                details="Mainstream encyclopedia entries",
            )
        )
        data_used.append(
            DataSource(
                name="Fact-check databases",
                cache_status="fresh",
                details="Verified fact-check sources (no fringe sources)",
            )
        )
    
    # Add readable sources from analysis
    existing_sources = {entry.name for entry in data_used}
    for source_name in analysis.get("sources_used", []):
        if source_name not in existing_sources:
            data_used.append(DataSource(name=source_name, cache_status="fresh"))
            existing_sources.add(source_name)

    # Build conclusion steps from confidence breakdown
    breakdown = analysis.get("confidence_breakdown", {})
    conclusion_steps: list[str] = []
    for metric, component in breakdown.items():
        score = component.get("score", 0)
        reason = component.get("reason", "Reason not provided.")
        conclusion_steps.append(f"{metric.replace('_', ' ').title()} ({score}/100): {reason}")
    if not conclusion_steps:
        conclusion_steps = verdict_bundle.how_we_got_conclusion.copy()

    limitations = analysis.get("limitations", [])
    if not limitations and context.limitations:
        limitations = context.limitations.copy()

    confidence_score: int = analysis.get("confidence_score", 0)
    verdict_text: str = analysis.get("verdict_text", verdict_bundle.verdict)

    return ConspiraciesResponse(
        summary=analysis["claim_text"],
        verdict=verdict_text,
        confidence=max(0.0, min(1.0, confidence_score / 100)),
        data_used=data_used,
        how_we_got_conclusion=conclusion_steps,
        long_term_outcome_example=verdict_text,
        limitations=limitations,
        guardrail_flags=guardrail_flags,
        model_version=os.getenv("CONSPIRACY_MODEL", "gpt-4o-mini"),
        evaluation_date=now_utc().isoformat(),
        claim_text=analysis["claim_text"],
        story_sections=analysis["story_sections"],
        claims_vs_evidence=analysis["claims_vs_evidence"],
        verdict_text=verdict_text,
        confidence_score=confidence_score,
        sources_used=analysis.get("sources_used", []),
        fuels_today=analysis.get("fuels_today", []),
    )

