"""Domain routing helpers shared by services."""

from __future__ import annotations

from ..schemas.theory import Domain

DOMAIN_KEYWORDS: dict[Domain, tuple[str, ...]] = {
    Domain.bets: ("odds", "parlay", "sportsbook", "bet", "spread"),
    Domain.crypto: ("token", "defi", "etherscan", "chain", "crypto"),
    Domain.stocks: ("ticker", "earnings", "dividend", "sec filing", "stock"),
    Domain.conspiracies: ("coverup", "deep state", "mkultra", "roswell", "conspiracy"),
    Domain.playlist: ("playlist", "youtube", "watchlist", "video mix", "curation"),
}


def route_domain(theory_text: str) -> Domain:
    """Naive keyword-based router (placeholder for classifier)."""

    lowered = theory_text.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return domain

    return Domain.stocks

