"""Run manager that orchestrates scraper + odds execution."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict

from ..db import db_models, get_session
from ..logging import logger
from ..models import IngestionConfig
from ..odds.synchronizer import OddsSynchronizer
from ..persistence import persist_game_payload
from ..scrapers.nba_sportsref import NBASportsReferenceScraper
from ..scrapers.ncaab_sportsref import NCAABSportsReferenceScraper


class ScrapeRunManager:
    def __init__(self) -> None:
        self.scrapers = {
            "NBA": NBASportsReferenceScraper(),
            "NCAAB": NCAABSportsReferenceScraper(),
        }
        self.odds_sync = OddsSynchronizer()

    def _update_run(self, run_id: int, **updates) -> None:
        with get_session() as session:
            run = session.get(db_models.SportsScrapeRun, run_id)
            if not run:
                return
            for key, value in updates.items():
                setattr(run, key, value)

    def run(self, run_id: int, config: IngestionConfig) -> dict:
        summary: Dict[str, int | str] = {"games": 0, "odds": 0}
        start = config.start_date or date.today()
        end = config.end_date or start
        scraper = self.scrapers.get(config.league_code)
        if not scraper and config.include_boxscores:
            raise RuntimeError(f"No scraper implemented for {config.league_code}")

        self._update_run(run_id, status="running", started_at=datetime.utcnow())

        try:
            if config.include_boxscores and scraper:
                with get_session() as session:
                    for game_payload in scraper.fetch_date_range(start, end):
                        persist_game_payload(session, game_payload)
                        summary["games"] += 1

            if config.include_odds:
                summary["odds"] = self.odds_sync.sync(config)

            self._update_run(
                run_id,
                status="success",
                finished_at=datetime.utcnow(),
                summary=f'Games: {summary["games"]}, Odds: {summary["odds"]}',
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("scrape_run_failed", run_id=run_id, error=str(exc))
            self._update_run(
                run_id,
                status="error",
                finished_at=datetime.utcnow(),
                error_details=str(exc),
            )
            raise

        return summary


