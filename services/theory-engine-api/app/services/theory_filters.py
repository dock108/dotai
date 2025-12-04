"""Apply theory filters to games and produce StoredBetRow entries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .bet_performance import StoredBetRow
from .odds_selection import get_last_seen_odds
from .. import db_models
from .utils.odds import american_to_decimal


async def apply_theory_filters(
    session,
    games_with_odds: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[StoredBetRow]:
    """Build StoredBetRow list with theory_flag set based on filters."""
    filters = config.get("filters", {}) if config else {}
    bet_types = config.get("bet_types", ["spread"])

    rows: list[StoredBetRow] = []
    for row in games_with_odds:
        game: db_models.SportsGame = row["game"]
        game_date = game.game_date.isoformat() if game.game_date else ""

        for bet_type in bet_types:
            odds_row = await get_last_seen_odds(
                session=session,
                game_id=game.id,
                market_type=bet_type,
                side=None,
            )
            if not odds_row:
                continue
            dec_odds = odds_row.market_decimal_odds or american_to_decimal(odds_row.price)
            if not dec_odds:
                continue

            theory_flag = _matches_filters(game, filters)
            rows.append(
                StoredBetRow(
                    game_id=str(game.id),
                    bet_type=bet_type,
                    selection=odds_row.side or "home",
                    market_decimal_odds=dec_odds,
                    result=_compute_result(game, bet_type),
                    theory_flag=theory_flag,
                    event_date=game_date,
                )
            )
    return rows


def _matches_filters(game: db_models.SportsGame, filters: dict[str, Any]) -> bool:
    """Very lightweight filter matcher (placeholder)."""
    # TODO: implement real filters like back_to_back, altitude, etc.
    return True if filters else True


def _compute_result(game: db_models.SportsGame, bet_type: str) -> str:
    """Placeholder result calculator based on scores."""
    if game.home_score is None or game.away_score is None:
        return "P"
    if bet_type == "spread":
        return "W" if game.home_score > game.away_score else "L"
    if bet_type == "total":
        return "W" if (game.home_score + game.away_score) > 0 else "L"
    return "P"

