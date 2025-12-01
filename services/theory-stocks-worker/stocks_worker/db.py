"""
Database helpers for the stocks worker service.

Reuses ORM models from theory-engine-api to keep a single source of truth
for schema and relationships.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .logging import logger

# Ensure the theory-engine-api app package is importable so we can reuse ORM models
THEORY_ENGINE_PATH = Path(__file__).resolve().parents[2] / "theory-engine-api"
if str(THEORY_ENGINE_PATH) not in sys.path:
    sys.path.append(str(THEORY_ENGINE_PATH))

try:
    from app import db_models  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Unable to import theory-engine-api app.db_models. "
        "Did you install the service dependencies?"
    ) from exc


engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=Session,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """Transactional database session context manager."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as exc:  # pragma: no cover
        session.rollback()
        logger.exception("db_session_rollback", error=str(exc))
        raise
    finally:
        session.close()


__all__ = ["get_session", "db_models", "engine"]


