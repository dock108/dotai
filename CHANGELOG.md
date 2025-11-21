# Changelog

All notable changes to the dock108 monorepo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Code Cleanup & Organization

#### Added
- **Backend utilities** (`services/theory-engine-api/app/utils/`):
  - `datetime_utils.py` - Centralized datetime functions (`now_utc()`, `now_local()`, `format_date_for_query()`)
  - `date_range_utils.py` - Date range building from presets (`build_date_range_from_preset()`, `get_default_date_range()`)
  - `error_handlers.py` - Standardized error response helpers
- **Frontend library modules** (`apps/highlight-channel-web/src/lib/`):
  - `constants.ts` - All constants (SPORT_OPTIONS, DATE_PRESETS, etc.)
  - `types.ts` - All TypeScript types/interfaces
  - `utils.ts` - Utility functions (buildQueryFromState, formatDuration, extractErrorInfo)
  - `presets.ts` - Preset configurations

#### Changed
- **Backend cleanup**:
  - Consolidated duplicate date range calculation logic
  - Standardized datetime imports across all files
  - Removed duplicate `_format_date_for_query()` function
  - Updated error handling to use centralized utilities
  - Removed `sports_search_example.py` (example file)
- **Frontend cleanup**:
  - Extracted constants, types, and utilities from page components
  - Simplified error handling using `extractErrorInfo()` utility
  - Reduced `page.tsx` from 851 lines by extracting shared code
  - Reduced `playlist/[id]/page.tsx` from 397 lines by extracting shared code
- **Documentation**:
  - Reorganized `docs/` folder with clear categorization
  - Updated `docs/README.md` with improved navigation
  - Updated root `README.md` with latest features and cleanup work

#### Removed
- `services/theory-engine-api/app/sports_search_example.py` - Example file removed
- Duplicate utility functions consolidated into shared modules

### Phase - Observability, Guardrails, and Documentation

#### Added
- **Structured logging** for highlight playlist requests:
  - User ID (or anonymous ID)
  - Query text and normalized signature
  - Cache hit vs miss tracking
  - YouTube API call counts
  - Final playlist length vs requested duration
- **Metrics endpoints**:
  - `GET /api/highlights/metrics` - JSON metrics (sports requested, avg duration, cache hit rate)
  - `GET /api/highlights/metrics/csv` - CSV export for simple dashboards
- **Enhanced guardrails**:
  - Block YouTube bypass/download attempts
  - Detect "pirate the whole broadcast" requests with polite refusal and alternative suggestion
  - Expanded copyright violation keyword detection
- **Legal disclaimers**:
  - Added disclaimer to all API responses: "This app builds playlists using public YouTube videos. We do not host or control the content."
  - No use of "SportsCenter" or trademarked branding

#### Documentation
- Updated `README.md` with Sports Highlight Channel feature overview and local dev instructions
- Created `docs/highlight-mvp.md` with constraints, limitations, and future ideas

## [Unreleased]

### Phase - Sports Highlight MVP: Frontend - "Build Your Own Sports Channel" UI

#### Added
- **New app**: `apps/highlight-channel-web` - Sports highlight channel builder
- **Landing page** (`/`):
  - Large text input for natural language requests
  - Quick preset chips (Last night's NFL, Today's MLB, Random bloopers, Deep dive on one team)
  - Promo link to AI Prompting Game
- **Query builder affordances**:
  - Sport chips (NFL, NBA, MLB, NHL, Soccer, Golf, F1) - appears after first parse
  - Date range picker (start/end dates)
  - Duration slider (15 min → 8 hours)
  - Content mix slider (Bloopers ↔ Highlights)
  - Auto-updates query and re-calls backend when changed
- **Playlist viewer** (`/playlist/:id`):
  - Video list with title, channel, duration, scores
  - "Play All on YouTube" button (constructs YouTube playlist URL)
  - Workday mode buttons (1h, 2h, 4h, 8h) for background channels
  - Explanation panel with:
    - Assumptions made during parsing
    - Filters applied
    - Ranking factors (scoring weights)
    - Coverage notes
    - Statistics (candidates found, selected, duration)
- **Docker configuration**:
  - Added `highlight-channel-web.Dockerfile`
  - Added to `docker-compose.yml` (port 3005)
  - Added nginx route for `highlights.dock108.ai`

### Phase - Sports Highlight MVP: API Endpoints

#### Added
- **Highlights API router** (`app/routers/highlights.py`):
  - `POST /api/highlights/plan` - Plan highlight playlist from user query
    - Runs guardrails, AI parsing, signature computation
    - Checks DB for cached non-stale playlists
    - Builds new playlist if needed (sync for MVP)
    - Returns playlist with cache_status ("cached" or "fresh")
  - `GET /api/highlights/{playlist_id}` - Retrieve playlist details
    - Includes playlist metadata, items, and explanation
- **Playlist building**:
  - `build_playlist_from_candidates()` - Selects videos to reach target duration ±10% tolerance
  - Converts HighlightRequestSpec to SportsSearchSpec
  - Generates explanation JSON with assumptions, filters, ranking factors, coverage notes
- **Database updates**:
  - Added `explanation` JSONB field to `playlists` table
  - Stores assumptions, filters_applied, ranking_factors, coverage_notes
- **Migration**: Updated `002_add_playlist_tables.py` to include explanation field
- **Documentation**: `docs/HIGHLIGHTS_API.md` with endpoint documentation

### Phase - Sports Highlight MVP: AI Layer - Parsing User Text

#### Added
- **Highlight request schema** (`packages/py-core/py_core/schemas/highlight_request.py`):
  - `HighlightRequestSpec` - Structured specification with sport, leagues, teams, date_range, content_mix, etc.
  - `HighlightRequestParseResult` - Parse result with confidence and clarification questions
  - `Sport` enum - Supported sports (NFL, NBA, MLB, NHL, NCAAF, NCAAB, PGA, F1, SOCCER, TENNIS, OTHER)
  - `LoopMode` enum - Playlist loop modes (single_playlist, loop_1h, loop_full_day)
  - `ContentMix` - Content type proportions (highlights, bloopers, top_plays, condensed, full_game, upsets)
  - `DateRange` - Flexible date specification (single_date, start_date/end_date, week, season)
- **AI parsing** (`app/highlight_parser.py`):
  - `parse_highlight_request()` - AI-powered parser using OpenAI
  - Loads system prompt from `ai_prompts/sports_highlight_channel.md`
  - Returns structured spec with confidence and clarification questions
- **System prompt** (`ai_prompts/sports_highlight_channel.md`):
  - Comprehensive prompt for parsing user text into structured specs
  - Handles ambiguous sports, duration interpretations, date parsing
  - Examples and parsing rules
- **Sports highlight guardrails** (`packages/py-core/py_core/guardrails/sports_highlights.py`):
  - `check_sports_highlight_guardrails()` - Sports-specific guardrail checks
  - Hard blocks: Copyright violations (full game reuploads, PPV reuploads)
  - Hard blocks: NSFW/violent content unrelated to sports
  - Soft flags: Sketchy content (leaked, unauthorized, fan uploads)
  - `normalize_sports_request()` - Text normalization
- **Dependencies**: Added `openai>=1.0.0,<2.0.0` to theory-engine-api

### Phase - Sports Highlight MVP: YouTube / Sports Ingestion Layer

#### Added
- **Sports-focused search** (`app/sports_search.py`):
  - `SportsSearchSpec` dataclass - Structured search specification
  - `build_search_queries()` - Generate YouTube search queries from spec
  - `search_youtube_sports()` - Async YouTube API search with filtering
  - Query templates: "{team} vs {opponent} highlights {date}", "{league} highlights {date}", etc.
  - Channel whitelists for official league/team channels
  - Duration filters based on content type (highlights: 5-15min, bloopers: <5min, etc.)
- **Highlight detection & scoring**:
  - `calculate_highlight_score()` - Multi-factor scoring function
  - `highlight_score` - Keyword detection (highlight, condensed, recap, top plays, bloopers)
  - `channel_reputation` - Official channels (1.0) > major networks (0.8) > others (0.5)
  - `view_count_normalized` - Log-scale normalization
  - `freshness_score` - Based on video publish date vs event date
  - `final_score` - Weighted combination for ranking
- **Helper functions**:
  - `get_channel_reputation_score()` - Channel reputation lookup
  - `get_duration_filters()` - Content-type-based duration ranges
  - `parse_iso_duration()` - Parse YouTube ISO 8601 duration strings
- **Example usage** - `app/sports_search_example.py` with usage examples

### Phase - Sports Highlight MVP: Data & Caching Design

#### Added
- **Playlist database schema**:
  - `playlist_queries` table - Stores normalized queries with signatures for caching
  - `playlists` table - Stores generated playlists with JSONB video items
  - `videos` table - Optional cached video metadata for deduplication
- **Staleness logic** (`app/playlist_staleness.py`):
  - `compute_stale_after()` - Compute staleness based on event recency
  - `is_stale()` - Check if playlist is stale
  - `should_refresh_playlist()` - Determine if refresh is needed
  - Rules: <2 days = 6 hours, 2-30 days = 3 days, >30 days = never expires
- **Query normalization** (`app/playlist_helpers.py`):
  - `PlaylistQuerySpec` dataclass - Structured query specification
  - `generate_normalized_signature()` - Generate hash signature for caching
  - `parse_query_to_spec()` - Placeholder for LLM-based query parsing
- **Database migration** - `002_add_playlist_tables.py` for new tables
- **Documentation** - `docs/PLAYLIST_DATABASE.md` with schema documentation

### Phase - Sports Highlight MVP: Cleanup Step

#### Removed
- Removed debug API endpoint (`apps/playlist-web/src/app/api/debug/route.ts`) - development-only code not needed in production

#### Deprecated
- Marked `apps/playlist-web/legacy-mvp/` folder as deprecated with clear documentation
- Added `DEPRECATED.md` file explaining the folder is for reference only

#### Documentation
- Created `docs/highlight-phase-notes.md` with comprehensive code audit
- Documented duplicate code, dead code, and refactoring opportunities
- Identified code to extract into shared packages for sports highlight feature

#### Changed
- Updated `apps/playlist-web/legacy-mvp/DEPRECATED.md` to clarify archive status

## [0.1.0] - 2024-11-18

### Added
- Initial monorepo structure with apps, services, and packages
- Theory engine API with domain-specific routers (bets, crypto, stocks, conspiracies, playlist)
- Frontend apps for each theory domain
- Shared UI kit with TheoryForm and TheoryCard components
- Playlist web app with YouTube integration
- Game web app (AI prompting game)
- Docker Compose deployment configuration for Hetzner
- Nginx reverse proxy with subdomain routing
- Data privacy model documentation
- Database models with privacy-first design

### Infrastructure
- Dockerfiles for all services and apps
- Nginx configuration for subdomain routing
- Deployment documentation
- Environment variable templates

