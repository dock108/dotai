from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

STORE_PATH = Path(os.environ.get("MICRO_MODEL_STORE", "/tmp/micro_model_runs.json"))


def _load_store() -> Dict[str, Any]:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_store(data: Dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, indent=2, default=str))


def save_run(run_id: str, payload: Dict[str, Any]) -> None:
    data = _load_store()
    data[run_id] = payload
    _save_store(data)


def load_run(run_id: str) -> Optional[Dict[str, Any]]:
    data = _load_store()
    return data.get(run_id)


def list_runs() -> Dict[str, Any]:
    return _load_store()

