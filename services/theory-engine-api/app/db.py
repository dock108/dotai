"""
Database connection and session management for theory-engine-api.

Provides async SQLAlchemy session management with proper transaction handling.
All database operations should use the `get_db()` dependency for FastAPI routes
or the `get_async_session()` context manager for standalone operations.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .config import settings
from .db_models import Base

engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session management.
    
    Provides a database session with automatic transaction handling:
    - Commits on successful completion
    - Rolls back on exceptions
    - Always closes the session
    
    Usage in FastAPI routes:
        @router.get("/endpoint")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            # Use db here
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session():
    """
    Context manager for async database sessions.
    
    Use this for standalone operations outside of FastAPI routes.
    Provides the same transaction handling as `get_db()`.
    
    Usage:
        async with get_async_session() as session:
            # Use session here
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database tables.
    
    Creates all tables defined in db_models.py if they don't exist.
    This is typically only used in development/testing. Production
    deployments should use Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close all database connections.
    
    Should be called during application shutdown to properly
    clean up connection pool resources.
    """
    await engine.dispose()

