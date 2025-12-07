from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MegaFeatureRow:
    id: str
    game_id: str
    features: Dict[str, Any]
    target: Any | None = None
    model_version: str = "v1"
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MegaModelArtifact:
    id: str
    version: str
    artifact_uri: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MegaTrainingRepository:
    """
    Stores feature rows and versioned mega-model artifacts.
    In-memory stub; replace with persistent storage later.
    """

    def __init__(self):
        self._features: Dict[str, MegaFeatureRow] = {}
        self._artifacts: Dict[str, MegaModelArtifact] = {}

    async def save_feature_row(self, row: MegaFeatureRow) -> MegaFeatureRow:
        self._features[row.id] = row
        return row

    async def bulk_save_feature_rows(self, rows: List[MegaFeatureRow]) -> List[MegaFeatureRow]:
        for r in rows:
            self._features[r.id] = r
        return rows

    async def list_feature_rows(self, model_version: Optional[str] = None) -> List[MegaFeatureRow]:
        rows = list(self._features.values())
        if model_version:
            rows = [r for r in rows if r.model_version == model_version]
        return rows

    async def save_artifact(self, artifact: MegaModelArtifact) -> MegaModelArtifact:
        self._artifacts[artifact.id] = artifact
        return artifact

    async def get_artifact(self, artifact_id: str) -> Optional[MegaModelArtifact]:
        return self._artifacts.get(artifact_id)

    async def list_artifacts(self, version: Optional[str] = None) -> List[MegaModelArtifact]:
        arts = list(self._artifacts.values())
        if version:
            arts = [a for a in arts if a.version == version]
        return arts



