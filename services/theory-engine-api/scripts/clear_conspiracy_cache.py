#!/usr/bin/env python3
"""Clear conspiracy theory context cache.

Usage:
    python scripts/clear_conspiracy_cache.py                    # Clear all conspiracy cache
    python scripts/clear_conspiracy_cache.py --query "text"     # Clear cache for specific query
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root + packages are importable when running as a script
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from py_core.data.cache import CacheKey  # noqa: E402
from py_core.data.fetchers import _get_cache  # noqa: E402


def clear_all_conspiracy_cache() -> int:
    """Clear all conspiracy theory cache entries."""
    cache = _get_cache()
    keys_to_remove: list[str] = []

    for key_hash, entry in cache._memory_cache.items():
        payload = entry.payload
        if payload.get("query") and ("wikipedia_data" in payload or "factcheck_data" in payload):
            keys_to_remove.append(key_hash)

    for key in keys_to_remove:
        del cache._memory_cache[key]

    cleared = len(keys_to_remove)
    print(f"✅ Cleared {cleared} conspiracy theory cache entries")
    return cleared


def clear_query_cache(query_text: str) -> int:
    """Clear cache for a specific query text."""
    cache = _get_cache()
    keys_to_remove: list[str] = []

    for key_hash, entry in cache._memory_cache.items():
        payload = entry.payload
        cached_query = payload.get("query", "")
        if query_text.lower() in cached_query.lower() or cached_query.lower() in query_text.lower():
            if "wikipedia_data" in payload or "factcheck_data" in payload:
                keys_to_remove.append(key_hash)

    for key in keys_to_remove:
        del cache._memory_cache[key]

    cleared = len(keys_to_remove)
    if cleared > 0:
        print(f"✅ Cleared {cleared} cache entries for '{query_text}'")
    else:
        print(f"❌ No cache entries found for '{query_text}'")
    return cleared


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--query" and len(sys.argv) > 2:
            clear_query_cache(sys.argv[2])
        elif sys.argv[1] in {"--help", "-h"}:
            print(__doc__)
        else:
            print("❌ Invalid arguments. Use --help for usage.")
            sys.exit(1)
    else:
        cleared = clear_all_conspiracy_cache()
        if cleared == 0:
            print("ℹ️  No conspiracy cache entries found to clear")


if __name__ == "__main__":
    main()


