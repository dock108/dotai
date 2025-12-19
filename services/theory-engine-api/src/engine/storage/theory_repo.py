from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class TheoryRecord:
    id: str
    name: str
    version: str = "v1"
    enabled: bool = True
    spec: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class TheoryRepository:
    """
    Simple in-memory CRUD for theories/specs/metadata.
    Swap with persistent backend later.
    """

    def __init__(self):
        self._store: Dict[str, TheoryRecord] = {}

    async def create(self, record: TheoryRecord) -> TheoryRecord:
        self._store[record.id] = record
        return record

    async def get(self, theory_id: str) -> Optional[TheoryRecord]:
        return self._store.get(theory_id)

    async def list(self, enabled_only: bool = False) -> List[TheoryRecord]:
        values = list(self._store.values())
        if enabled_only:
            values = [r for r in values if r.enabled]
        return values

    async def update(self, theory_id: str, **fields: Any) -> Optional[TheoryRecord]:
        rec = self._store.get(theory_id)
        if not rec:
            return None
        for k, v in fields.items():
            if hasattr(rec, k):
                setattr(rec, k, v)
            else:
                rec.metadata[k] = v
        rec.updated_at = datetime.utcnow()
        return rec

    async def delete(self, theory_id: str) -> bool:
        return self._store.pop(theory_id, None) is not None




