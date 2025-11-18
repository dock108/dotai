"""Brutal honesty scoring helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..schemas.theory import Domain


@dataclass(slots=True)
class VerdictBundle:
    verdict: str
    confidence: float
    reasoning: str
    long_term_example: str


def compute_domain_verdict(domain: Domain, theory_text: str) -> VerdictBundle:
    """Simple heuristic scorer placeholder."""

    lowered = theory_text.lower()
    if domain == Domain.bets:
        edge_hint = "positive edge" if "model" in lowered else "insufficient edge"
        return VerdictBundle(
            verdict="Proceed with caution",
            confidence=0.42,
            reasoning=f"Bets need a {edge_hint}; verify closing line value before staking.",
            long_term_example="If you stake $100 per week without edge, expect bankroll drag within 60 days.",
        )
    if domain == Domain.crypto:
        return VerdictBundle(
            verdict="High volatility",
            confidence=0.35,
            reasoning="Token narratives shift quickly; confirm on-chain liquidity + unlock schedules.",
            long_term_example="DCA $100/mo only if you can stomach 70% drawdowns over 12 months.",
        )
    if domain == Domain.stocks:
        return VerdictBundle(
            verdict="Needs fundamentals",
            confidence=0.55,
            reasoning="Compare revenue growth vs. margin compression before taking a position.",
            long_term_example="Investing $100/mo at 6% CAGR compounds to ~$6.7k over 5 years; below-market returns if thesis misses.",
        )
    if domain == Domain.conspiracies:
        return VerdictBundle(
            verdict="Extraordinary claim",
            confidence=0.28,
            reasoning="Source triangulation is thin; rely on peer-reviewed or official reports.",
            long_term_example="Treat as media literacy exercise rather than actionable intel.",
        )
    # playlist
    return VerdictBundle(
        verdict="Playable draft",
        confidence=0.7,
        reasoning="Mix covers intro/context/deep dive; test transitions with real listeners.",
        long_term_example="Curate 10 tracks weekly; after 3 months you'll have 12+ themed playlists ready for automation.",
    )

