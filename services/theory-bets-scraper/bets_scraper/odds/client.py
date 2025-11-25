"""Odds API client for pulling mainline closing prices."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, List
from urllib.parse import urlencode

import httpx

from ..config import settings
from ..logging import logger
from ..models import NormalizedOddsSnapshot, TeamIdentity


SPORT_KEY_MAP = {
    "NBA": "basketball_nba",
    "NCAAB": "basketball_ncaab",
    "NFL": "americanfootball_nfl",
    "NCAAF": "americanfootball_ncaaf",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
}

MARKET_TYPES = {
    "spreads": "spread",
    "totals": "total",
    "h2h": "moneyline",
}


class OddsAPIClient:
    def __init__(self) -> None:
        if not settings.odds_api_key:
            logger.warning("odds_api_key_missing", message="ODDS_API_KEY not configured; odds sync disabled.")
        self.client = httpx.Client(
            base_url=settings.odds_config.base_url,
            headers={"User-Agent": "dock108-odds-sync/1.0"},
            timeout=settings.odds_config.request_timeout_seconds,
        )

    def _sport_key(self, league_code: str) -> str | None:
        return SPORT_KEY_MAP.get(league_code.upper())

    def fetch_mainlines(
        self,
        league_code: str,
        start_date: date,
        end_date: date,
        books: list[str] | None = None,
    ) -> list[NormalizedOddsSnapshot]:
        if not settings.odds_api_key:
            return []

        sport_key = self._sport_key(league_code)
        if not sport_key:
            logger.warning("unsupported_league_for_odds", league=league_code)
            return []

        from datetime import timezone
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        params = {
            "apiKey": settings.odds_api_key,
            "regions": "us",
            "markets": ",".join(MARKET_TYPES.keys()),
            "oddsFormat": "american",
            "commenceTimeFrom": start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commenceTimeTo": end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if books:
            params["bookmakers"] = ",".join(books)

        response = self.client.get(f"/sports/{sport_key}/odds", params=params)
        if response.status_code != 200:
            logger.error("odds_api_error", status=response.status_code, body=response.text)
            return []

        payload = response.json()
        logger.info("odds_api_response", league=league_code, event_count=len(payload) if isinstance(payload, list) else 0)
        snapshots: list[NormalizedOddsSnapshot] = []
        for event in payload:
            game_date = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
            home_team = TeamIdentity(
                league_code=league_code,
                name=event["home_team"],
                short_name=event["home_team"],
                abbreviation=(event["home_team"][:6]).upper(),
            )
            away_team = TeamIdentity(
                league_code=league_code,
                name=event["away_team"],
                short_name=event["away_team"],
                abbreviation=(event["away_team"][:6]).upper(),
            )
            for bookmaker in event.get("bookmakers", []):
                if books and bookmaker["key"] not in books:
                    continue
                for market in bookmaker.get("markets", []):
                    market_type = MARKET_TYPES.get(market["key"])
                    if not market_type:
                        continue
                    for outcome in market.get("outcomes", []):
                        snapshots.append(
                            NormalizedOddsSnapshot(
                                league_code=league_code,
                                book=bookmaker["title"],
                                market_type=market_type,  # type: ignore[arg-type]
                                side=outcome.get("name"),
                                line=outcome.get("point"),
                                price=outcome.get("price"),
                                observed_at=datetime.fromisoformat(bookmaker["last_update"].replace("Z", "+00:00")),
                                home_team=home_team,
                                away_team=away_team,
                                game_date=game_date,
                                source_key=market.get("key"),
                                is_closing_line=True,
                                raw_payload=outcome,
                            )
                        )
        return snapshots


