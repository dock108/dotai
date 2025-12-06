from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Protocol, Sequence

from engine.common.micro_model import MicroModel
from engine.common.feature_builder import FeatureBuilder
from engine.common.result_schema import BacktestResult


class GameLoader(Protocol):
    async def load_games(self, league_id: int, seasons: Sequence[int] | None = None) -> Iterable[Dict[str, Any]]:
        ...


class LiveOddsProvider(Protocol):
    async def current_odds(self, league_id: int) -> Iterable[Dict[str, Any]]:
        ...


class OddsHistoryProvider(Protocol):
    async def odds_history(self, league_id: int) -> Iterable[Dict[str, Any]]:
        ...


class ResultsRepository(Protocol):
    async def save_backtest(self, items: List[BacktestResult]) -> None:
        ...


@dataclass
class PipelineContext:
    league_id: int
    seasons: Sequence[int] | None = None
    feature_mode: str = "full"


