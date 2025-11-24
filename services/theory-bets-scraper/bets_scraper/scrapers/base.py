"""Base classes for sport-specific scrapers."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, Iterator, Sequence

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from ..logging import logger
from ..models import NormalizedGame


class ScraperError(RuntimeError):
    """Raised when a scraper encounters an unrecoverable error."""


class BaseSportsReferenceScraper:
    """Shared utilities for scraping Sports Reference scoreboards."""

    sport: str  # e.g., "nba" or "cbb"
    league_code: str
    base_url: str

    def __init__(self, timeout_seconds: int = 20) -> None:
        self.client = httpx.Client(timeout=timeout_seconds, headers={"User-Agent": "dock108-scraper/1.0"})

    def iter_dates(self, start: date, end: date) -> Iterator[date]:
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    def scoreboard_url(self, day: date) -> str:
        return f"{self.base_url}?month={day.month}&day={day.day}&year={day.year}"

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def fetch_html(self, url: str) -> BeautifulSoup:
        response = self.client.get(url)
        if response.status_code != 200:
            raise ScraperError(f"Failed to fetch {url} ({response.status_code})")
        return BeautifulSoup(response.text, "lxml")

    def fetch_games_for_date(self, day: date) -> Sequence[NormalizedGame]:
        raise NotImplementedError

    def fetch_date_range(self, start: date, end: date) -> Iterable[NormalizedGame]:
        for day in self.iter_dates(start, end):
            try:
                games = self.fetch_games_for_date(day)
                for game in games:
                    yield game
            except ScraperError as exc:
                logger.error("scraper_date_error", day=str(day), error=str(exc))


