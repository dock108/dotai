from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MicroResultRecord:
    id: str
    event_id: str
    market: str
    ev: float | None
    outcome: Any | None
    pnl: float | None
    odds: float | None
    implied_prob: float | None
    features: Dict[str, Any] = field(default_factory=dict)
    source: str = "backtest"  # "backtest" | "live"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MicroResultsRepository:
    """
    Stores one row per triggered bet historically and per live opportunity.
    In-memory stub; replace with DB-backed implementation later.
    """

    def __init__(self):
        self._store: Dict[str, MicroResultRecord] = {}

    async def save(self, record: MicroResultRecord) -> MicroResultRecord:
        self._store[record.id] = record
        return record

    async def bulk_save(self, records: List[MicroResultRecord]) -> List[MicroResultRecord]:
        for r in records:
            self._store[r.id] = r
        return records

    async def get(self, record_id: str) -> Optional[MicroResultRecord]:
        return self._store.get(record_id)

    async def list(self, source: Optional[str] = None) -> List[MicroResultRecord]:
        values = list(self._store.values())
        if source:
            values = [r for r in values if r.source == source]
        return values



