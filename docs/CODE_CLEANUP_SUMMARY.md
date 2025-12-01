# Code Cleanup Summary

This document consolidates cleanup summaries from all services and apps in the dock108 monorepo.

## Overview

During the cleanup sprint, we focused on:
- **Deduplication**: Removing duplicate code and patterns
- **Modularization**: Extracting common utilities and components
- **Consolidation**: Centralizing shared functionality
- **Consistency**: Standardizing patterns across services

---

## Theory Bets Web (`apps/theory-bets-web`)

### Completed ✅

#### 1. Shared Utilities Created
- **`src/lib/utils/status.ts`**: Status handling utilities
  - `getStatusClass()` - Get CSS class name for status
  - `getStatusColor()` - Get background color for status
  - `getStatusLabel()` - Get human-readable status label

- **`src/lib/utils/dateFormat.ts`**: Date formatting utilities
  - `formatDate()` - Format date to localized string
  - `formatDateTime()` - Format date and time
  - `formatDateRange()` - Format date range as "start → end"
  - `formatDateInput()` - Format for form inputs (YYYY-MM-DD)
  - `getQuickDateRange()` - Get date range for quick filters

- **`src/lib/utils/index.ts`**: Centralized utility exports

#### 2. Shared Components Created
- **`src/components/admin/StatusBadge.tsx`**: Reusable status badge component
- **`src/components/admin/LoadingState.tsx`**: Reusable loading state
- **`src/components/admin/ErrorState.tsx`**: Reusable error state
- **`src/components/admin/index.ts`**: Centralized component exports

#### 3. Shared Hooks Created
- **`src/lib/hooks/useScrapeRuns.ts`**: Hook for fetching scrape runs with loading/error states
- **`src/lib/hooks/useGames.ts`**: Hook for fetching games with filters and pagination

#### 4. Pages Updated
- ✅ `src/app/admin/page.tsx` - Uses shared `getStatusClass` utility
- ✅ `src/app/admin/theory-bets/page.tsx` - Uses shared `getStatusClass` utility
- ✅ `src/app/admin/games/page.tsx` - Uses `getQuickDateRange` and `formatDate`
- ✅ `src/app/admin/ingestion/page.tsx` - Uses `useScrapeRuns` hook and `formatDateTime`
- ✅ `src/app/admin/theory-bets/ingestion/page.tsx` - Uses `useScrapeRuns` hook and `formatDateTime`

### Remaining Work 🔄

1. **Consolidate duplicate admin pages**: Decide between `/admin/*` and `/admin/theory-bets/*` structures
2. **Update remaining 8 pages** to use shared date formatting utilities
3. **CSS module cleanup**: Consolidate duplicate styles and create shared variables

---

## Theory Bets Scraper (`services/theory-bets-scraper`)

### Completed ✅

#### 1. Scraper Registry Pattern
- **`bets_scraper/scrapers/__init__.py`**: Created centralized scraper registry
  - `get_scraper(league_code)` - Get scraper instance by league code
  - `get_all_scrapers()` - Get all registered scrapers as dict
  - Eliminates hardcoded imports in `run_manager.py`

#### 2. Shared HTML Parsing Utilities
- **`bets_scraper/utils/html_parsing.py`**: Common HTML parsing functions
  - `find_table_by_id()` - Find table with alternate ID fallback
  - `find_player_table()` - Find player stats table
  - `extract_team_stats_from_table()` - Extract stats from tfoot
  - `get_table_ids_on_page()` - Debug helper for table discovery

#### 3. Shared Database Query Utilities
- **`bets_scraper/utils/db_queries.py`**: Common database queries
  - `get_league_id()` - Get league ID by code
  - `count_team_games()` - Count games for a team
  - `has_player_boxscores()` - Check if game has player stats
  - `has_odds()` - Check if game has odds
  - `find_games_in_date_range()` - Find games with filters

#### 4. Shared Datetime Utilities
- **`bets_scraper/utils/datetime_utils.py`**: Centralized datetime handling
  - `utcnow()` - Get current UTC datetime (replaces `datetime.utcnow()`)
  - `date_to_datetime_range()` - Convert date to datetime range
  - `date_window_for_matching()` - Get date window for game matching

#### 5. Updated Files to Use Shared Utilities
- ✅ `bets_scraper/services/run_manager.py` - Uses scraper registry and shared queries
- ✅ `bets_scraper/persistence.py` - Uses `utcnow()`, `get_league_id()`, `date_window_for_matching()`
- ✅ `bets_scraper/celery_app.py` - Uses `utcnow()`
- ✅ All scraper implementations (NBA, NFL, MLB, NHL, NCAAB, NCAAF) - Use shared HTML parsing utilities

### Benefits

1. **Easier to add new scrapers**: Just register in `__init__.py`, no need to update `run_manager.py`
2. **Consistent HTML parsing**: All scrapers use same utilities, reducing bugs
3. **Centralized datetime handling**: Single source of truth for UTC time
4. **Reusable database queries**: Common queries extracted for reuse
5. **Better maintainability**: Changes to common patterns only need to be made once

---

## Theory Engine API (`services/theory-engine-api`)

### Completed ✅

#### 1. Replaced `datetime.utcnow()` with `now_utc()`
- ✅ `app/main.py` - Uses `now_utc()` from utils
- ✅ `app/routers/bets.py` - Uses `now_utc()`
- ✅ `app/routers/crypto.py` - Uses `now_utc()`
- ✅ `app/routers/stocks.py` - Uses `now_utc()`
- ✅ `app/routers/conspiracies.py` - Uses `now_utc()`
- ✅ `app/routers/strategy.py` - Uses `now_utc()` (all instances)
- ✅ `app/routers/stocks_strategy.py` - Uses `now_utc()` (all instances)
- ✅ `app/routers/strategy_models.py` - Uses `now_utc()`
- ✅ `app/metrics.py` - Uses `now_utc()` (all instances)
- ✅ `app/highlight_parser.py` - Uses `now_utc()`

#### 2. Created Shared Serialization Utilities
- **`app/utils/serialization.py`**: Common serialization functions
  - `serialize_datetime()` - Serialize datetime to ISO string
  - `serialize_date()` - Serialize date to ISO date string
  - `serialize_jsonb_field()` - Serialize JSONB fields
  - `flatten_stats_for_response()` - Flatten nested stats for API responses

#### 3. Created Common Router Utilities
- **`app/routers/common.py`**: Shared router patterns
  - `evaluate_guardrails_and_context()` - Common guardrail + context pattern
  - `build_data_used_list()` - Build data sources list from context

#### 4. Updated Utils Exports
- **`app/utils/__init__.py`**: Added serialization utilities to exports

#### 5. Updated Sports Data Router
- ✅ `app/routers/sports_data.py` - Uses `flatten_stats_for_response()` for player stats

### Remaining Work 🔄

1. **Consolidate duplicate date formatting**: `format_date_for_query()` exists in both `datetime_utils.py` and `sports_search.py`
2. **Refactor routers to use common patterns**: All routers have similar guardrail/context patterns
3. **Extract common response models**: Many routers have similar response structures

### Benefits

1. **Consistent datetime handling**: All code uses `now_utc()` instead of deprecated `datetime.utcnow()`
2. **Reusable serialization**: Common patterns extracted for consistency
3. **Shared router patterns**: Common guardrail/context patterns available for reuse
4. **Better maintainability**: Changes to common patterns only need to be made once
5. **Type safety**: Centralized utilities ensure consistent return types

---

## Summary

All three services have been significantly cleaned up with:
- **Centralized utilities** for common operations
- **Reduced duplication** across codebases
- **Consistent patterns** for similar functionality
- **Better maintainability** through shared code
- **Type safety** improvements

The cleanup improves code quality, reduces bugs, and makes future development easier.

