#!/usr/bin/env python3
"""Clear playlist cache from database.

Usage:
    python scripts/clear_cache.py                    # Clear all cache
    python scripts/clear_cache.py --query "text"     # Clear cache for specific query
    python scripts/clear_cache.py --sport NFL        # Clear cache for specific sport
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure project root is on sys.path so `app` imports work when running from scripts/
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import AsyncSessionLocal, engine  # noqa: E402
from app.db_models import Playlist, PlaylistQuery  # noqa: E402


async def clear_all_cache() -> None:
    """Clear all playlist cache."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(delete(Playlist))
            playlists_deleted = result.rowcount

            result = await session.execute(delete(PlaylistQuery))
            queries_deleted = result.rowcount

            await session.commit()
            print(f"✅ Cleared cache: {playlists_deleted} playlists, {queries_deleted} queries")
        except Exception as exc:  # pragma: no cover - maintenance script
            await session.rollback()
            print(f"❌ Error clearing cache: {exc}")
            raise


async def clear_query_cache(query_text: str) -> None:
    """Clear cache for a specific query text."""
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(PlaylistQuery).where(PlaylistQuery.query_text.ilike(f"%{query_text}%"))
            result = await session.execute(stmt)
            queries = result.scalars().all()

            if not queries:
                print(f"❌ No queries found matching: {query_text}")
                return

            query_ids = [q.id for q in queries]

            result = await session.execute(delete(Playlist).where(Playlist.query_id.in_(query_ids)))
            playlists_deleted = result.rowcount

            result = await session.execute(delete(PlaylistQuery).where(PlaylistQuery.id.in_(query_ids)))
            queries_deleted = result.rowcount

            await session.commit()
            print(f"✅ Cleared cache for '{query_text}': {playlists_deleted} playlists, {queries_deleted} queries")
        except Exception as exc:  # pragma: no cover - maintenance script
            await session.rollback()
            print(f"❌ Error clearing cache: {exc}")
            raise


async def clear_sport_cache(sport: str) -> None:
    """Clear cache for a specific sport."""
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(PlaylistQuery).where(PlaylistQuery.sport == sport.upper())
            result = await session.execute(stmt)
            queries = result.scalars().all()

            if not queries:
                print(f"❌ No queries found for sport: {sport}")
                return

            query_ids = [q.id for q in queries]

            result = await session.execute(delete(Playlist).where(Playlist.query_id.in_(query_ids)))
            playlists_deleted = result.rowcount

            result = await session.execute(delete(PlaylistQuery).where(PlaylistQuery.id.in_(query_ids)))
            queries_deleted = result.rowcount

            await session.commit()
            print(f"✅ Cleared cache for sport '{sport}': {playlists_deleted} playlists, {queries_deleted} queries")
        except Exception as exc:  # pragma: no cover - maintenance script
            await session.rollback()
            print(f"❌ Error clearing cache: {exc}")
            raise


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--query" and len(sys.argv) > 2:
            await clear_query_cache(sys.argv[2])
        elif sys.argv[1] == "--sport" and len(sys.argv) > 2:
            await clear_sport_cache(sys.argv[2])
        elif sys.argv[1] in {"--help", "-h"}:
            print(__doc__)
        else:
            print("❌ Invalid arguments. Use --help for usage.")
            sys.exit(1)
    else:
        response = input("⚠️  This will clear ALL playlist cache. Continue? (yes/no): ")
        if response.lower() == "yes":
            await clear_all_cache()
        else:
            print("Cancelled.")


if __name__ == "__main__":
    asyncio.run(main())


