"""Odds synchronization utilities."""

from __future__ import annotations

from datetime import date

from ..db import get_session
from ..logging import logger
from ..models import IngestionConfig
from ..persistence import upsert_odds
from .client import OddsAPIClient


class OddsSynchronizer:
    def __init__(self) -> None:
        self.client = OddsAPIClient()

    def sync(self, config: IngestionConfig) -> int:
        if not config.include_odds:
            return 0
        start = config.start_date or date.today()
        end = config.end_date or start
        snapshots = self.client.fetch_mainlines(config.league_code, start, end, config.include_books)
        logger.info("odds_snapshots_fetched", league=config.league_code, count=len(snapshots))
        if not snapshots:
            logger.warning("no_odds_snapshots", league=config.league_code, start=start, end=end)
            return 0

        inserted = 0
        skipped = 0
        with get_session() as session:
            for snapshot in snapshots:
                try:
                    upsert_odds(session, snapshot)
                    inserted += 1
                except Exception as exc:
                    logger.warning("odds_upsert_failed", error=str(exc), game_date=snapshot.game_date)
                    skipped += 1
        logger.info("odds_sync_complete", league=config.league_code, inserted=inserted, skipped=skipped)
        return inserted


