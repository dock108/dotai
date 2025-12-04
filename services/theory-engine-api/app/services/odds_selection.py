"""Helpers for selecting last-seen odds snapshots."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import db_models


async def get_last_seen_odds(
    session: AsyncSession,
    game_id: int,
    market_type: str,
    side: str | None = None,
) -> db_models.SportsGameOdds | None:
    """Return the single best 'last seen' odds row for a game/market/side.

    Priority:
    1) Most recent closing line (`is_closing_line=True`) before now
    2) Otherwise, most recent snapshot for that market/side
    """
    now_ts = datetime.utcnow()

    def _base_stmt() -> Select:
        stmt: Select = select(db_models.SportsGameOdds).where(
            db_models.SportsGameOdds.game_id == game_id,
            db_models.SportsGameOdds.market_type == market_type,
        )
        if side:
            stmt = stmt.where(db_models.SportsGameOdds.side == side)
        return stmt

    # Prefer closing line
    closing_stmt = (
        _base_stmt()
        .where(db_models.SportsGameOdds.is_closing_line.is_(True))
        .where(db_models.SportsGameOdds.observed_at <= now_ts)
        .order_by(desc(db_models.SportsGameOdds.observed_at))
        .limit(1)
    )
    closing_result = await session.execute(closing_stmt)
    closing_row = closing_result.scalar_one_or_none()
    if closing_row:
        return closing_row

    # Fallback to most recent snapshot
    fallback_stmt = (
        _base_stmt()
        .order_by(desc(db_models.SportsGameOdds.observed_at))
        .limit(1)
    )
    fallback_result = await session.execute(fallback_stmt)
    return fallback_result.scalar_one_or_none()

