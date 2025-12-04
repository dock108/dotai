"""Historical data retrieval helpers for theory runs."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import db_models
from .odds_selection import get_last_seen_odds


async def get_historical_games(
    session: AsyncSession,
    sport: str,
    seasons: list[str],
    last_n_days: int,
) -> list[dict[str, Any]]:
    """Fetch historical games with last-seen odds snapshots.

    Returns a lightweight dict list with game info and odds.
    """
    # Map sport string to league_code (assume uppercase)
    league_code = sport.upper()
    cutoff = datetime.utcnow() - timedelta(days=last_n_days)

    stmt: Select = (
        select(db_models.SportsGame)
        .join(db_models.SportsLeague)
        .where(db_models.SportsLeague.code == league_code)
        .where(db_models.SportsGame.game_date >= cutoff)
        .order_by(desc(db_models.SportsGame.game_date))
    )
    result = await session.execute(stmt)
    games = result.scalars().unique().all()

    rows: list[dict[str, Any]] = []
    for game in games:
        odds_row = await get_last_seen_odds(
            session=session,
            game_id=game.id,
            market_type="spread",
            side="home",
        )
        rows.append(
            {
                "game": game,
                "odds": odds_row,
            }
        )
    return rows

