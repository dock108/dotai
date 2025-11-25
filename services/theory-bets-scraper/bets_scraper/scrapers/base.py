"""Base classes for sport-specific scrapers."""

from __future__ import annotations

import random
import time
from datetime import date, timedelta
from typing import Iterable, Iterator, Sequence

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..logging import logger
from ..models import NormalizedGame


class ScraperError(RuntimeError):
    """Raised when a scraper encounters an unrecoverable error."""


class BaseSportsReferenceScraper:
    """Shared utilities for scraping Sports Reference scoreboards."""

    sport: str  # e.g., "nba" or "cbb"
    league_code: str
    base_url: str

    def __init__(self, timeout_seconds: int | None = None) -> None:
        timeout = timeout_seconds or settings.scraper_config.request_timeout_seconds
        self.client = httpx.Client(timeout=timeout, headers={"User-Agent": "dock108-scraper/1.0"})
        self._last_request_time = 0.0
        self._min_request_interval = settings.scraper_config.min_request_interval
        self._rate_limit_wait = settings.scraper_config.rate_limit_wait_seconds
        self._jitter_range = settings.scraper_config.jitter_range
        self._day_delay_min = settings.scraper_config.day_delay_min
        self._day_delay_max = settings.scraper_config.day_delay_max
        self._error_delay_min = settings.scraper_config.error_delay_min
        self._error_delay_max = settings.scraper_config.error_delay_max

    def iter_dates(self, start: date, end: date) -> Iterator[date]:
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    def scoreboard_url(self, day: date) -> str:
        return f"{self.base_url}?month={day.month}&day={day.day}&year={day.year}"

    @retry(wait=wait_exponential(multiplier=2, min=30, max=120), stop=stop_after_attempt(2))
    def fetch_html(self, url: str) -> BeautifulSoup:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            wait_time = self._min_request_interval - elapsed + random.uniform(0, self._jitter_range)
            time.sleep(wait_time)
        self._last_request_time = time.time()
        
        response = self.client.get(url)
        if response.status_code == 429:
            logger.warning("rate_limit_hit", url=url, wait_seconds=self._rate_limit_wait)
            time.sleep(self._rate_limit_wait)
            raise ScraperError(f"Rate limited: {url} (429)")
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
                time.sleep(random.uniform(self._day_delay_min, self._day_delay_max))
            except ScraperError as exc:
                logger.error("scraper_date_error", day=str(day), error=str(exc))
                time.sleep(random.uniform(self._error_delay_min, self._error_delay_max))
                continue
