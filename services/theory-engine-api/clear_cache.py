#!/usr/bin/env python3
"""Clear playlist cache from database.

Usage:
    python clear_cache.py                    # Clear all cache
    python clear_cache.py --query "text"     # Clear cache for specific query
    python clear_cache.py --sport NFL        # Clear cache for specific sport
"""

import asyncio
import sys
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal, engine
from app.db_models import Playlist, PlaylistQuery


async def clear_all_cache():
    """Clear all playlist cache."""
    async with AsyncSessionLocal() as session:
        try:
            # Delete all playlists first (due to foreign key constraint)
            result = await session.execute(delete(Playlist))
            playlists_deleted = result.rowcount
            
            # Delete all queries
            result = await session.execute(delete(PlaylistQuery))
            queries_deleted = result.rowcount
            
            await session.commit()
            print(f"✅ Cleared cache: {playlists_deleted} playlists, {queries_deleted} queries")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error clearing cache: {e}")
            raise


async def clear_query_cache(query_text: str):
    """Clear cache for a specific query text."""
    async with AsyncSessionLocal() as session:
        try:
            # Find queries matching the text
            stmt = select(PlaylistQuery).where(PlaylistQuery.query_text.ilike(f"%{query_text}%"))
            result = await session.execute(stmt)
            queries = result.scalars().all()
            
            if not queries:
                print(f"❌ No queries found matching: {query_text}")
                return
            
            query_ids = [q.id for q in queries]
            
            # Delete playlists for these queries
            result = await session.execute(
                delete(Playlist).where(Playlist.query_id.in_(query_ids))
            )
            playlists_deleted = result.rowcount
            
            # Delete queries
            result = await session.execute(
                delete(PlaylistQuery).where(PlaylistQuery.id.in_(query_ids))
            )
            queries_deleted = result.rowcount
            
            await session.commit()
            print(f"✅ Cleared cache for '{query_text}': {playlists_deleted} playlists, {queries_deleted} queries")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error clearing cache: {e}")
            raise


async def clear_sport_cache(sport: str):
    """Clear cache for a specific sport."""
    async with AsyncSessionLocal() as session:
        try:
            # Find queries for this sport
            stmt = select(PlaylistQuery).where(PlaylistQuery.sport == sport.upper())
            result = await session.execute(stmt)
            queries = result.scalars().all()
            
            if not queries:
                print(f"❌ No queries found for sport: {sport}")
                return
            
            query_ids = [q.id for q in queries]
            
            # Delete playlists for these queries
            result = await session.execute(
                delete(Playlist).where(Playlist.query_id.in_(query_ids))
            )
            playlists_deleted = result.rowcount
            
            # Delete queries
            result = await session.execute(
                delete(PlaylistQuery).where(PlaylistQuery.id.in_(query_ids))
            )
            queries_deleted = result.rowcount
            
            await session.commit()
            print(f"✅ Cleared cache for sport '{sport}': {playlists_deleted} playlists, {queries_deleted} queries")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error clearing cache: {e}")
            raise


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--query" and len(sys.argv) > 2:
            await clear_query_cache(sys.argv[2])
        elif sys.argv[1] == "--sport" and len(sys.argv) > 2:
            await clear_sport_cache(sys.argv[2])
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
        else:
            print("❌ Invalid arguments. Use --help for usage.")
            sys.exit(1)
    else:
        # Clear all cache
        response = input("⚠️  This will clear ALL playlist cache. Continue? (yes/no): ")
        if response.lower() == "yes":
            await clear_all_cache()
        else:
            print("Cancelled.")


if __name__ == "__main__":
    asyncio.run(main())

