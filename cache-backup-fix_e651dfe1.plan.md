---
name: cache-backup-fix
overview: Back up existing game_data cache from docker, inspect cache path logic, and fix year-directory handling without wiping cache.
todos:
  - id: find-cache-code
    content: Identify cache base dir and path scheme in theory bets code
    status: pending
  - id: confirm-container
    content: Determine container storing cache and its path/mount
    status: pending
  - id: backup-cache
    content: Copy game_data from container to local backup folder
    status: pending
  - id: fix-cache-path
    content: Adjust cache path logic to use correct year derivation
    status: pending
  - id: redeploy-verify
    content: Rebuild/restart and verify new cache paths without wiping old data
    status: pending
---

# Cache Backup & Path Fix

## Goals

- Safely back up current `game_data` cache from the running theory bets stack to local storage.
- Identify container + on-disk cache location used by theory bets caching.
- Fix cache path logic so entries do not fall under an incorrect default year (e.g., `.../2025/...` when game year differs).

## Steps

1. **Locate cache root in code**

- Read theory bets caching code/config (likely in scraper/API) to confirm cache base dir (e.g., `/app/game_data`) and path scheme (league/year/date/team).

2. **Confirm container + mount**

- Inspect compose/service definitions to see which container holds the cache (likely `dock108-theory-api`) and whether `game_data` is volume-mapped; record exact in-container path.

3. **Back up cache without wiping**

- From host, `docker cp <container>:/app/game_data ./cache-backup-YYYYMMDD-HHMM/` (or equivalent) to store a local copy.

4. **Fix path logic**

- Update caching code to derive the year from the game date (or omit year dir) instead of a default/current year; ensure cache keys remain stable across leagues.

5. **Redeploy and verify**

- Rebuild/restart theory-engine-api (and any scraper service if needed), then verify new cache paths are created correctly and old cache is intact in backup.

## Implementation Todos

- find-cache-code: Identify cache base dir and path scheme in theory bets code.
- confirm-container: Determine which container stores cache and its path/mount.
- backup-cache: Copy `game_data` from container to local backup folder.
- fix-cache-path: Adjust cache path logic to use correct year derivation.
- redeploy-verify: Rebuild/restart and verify new cache paths without wiping old data.