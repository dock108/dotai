# Sports Highlight Flow (Current State)

> **Note**: This document describes the current implementation. Some gaps mentioned below have been addressed with the guided UI builder.

## 1. Frontend (apps/highlight-channel-web)

- Home page (`src/app/page.tsx`) exposes a **guided UI builder** with:
  - Sport checklists (multi-select)
  - Filter chips for teams, players, play types (up to 5 each)
  - Date preset buttons (Last 48 hours, Last 7 days, etc.) and custom date ranges
  - Duration slider (1-10 hours) with preset buttons
  - Optional comments field
- On submit it calls `HighlightsAPI.planPlaylist` from `@dock108/js-core`, sending both structured fields and `query_text`.
- When the plan succeeds, the user is redirected to `/playlist/[id]`, which invokes `HighlightsAPI.getPlaylist` to render final clips and explanation.
- The builder provides structured input while still allowing natural language via the comments field.

### Recent Improvements

- ✅ Guided UI builder with structured input (sports, teams, players, play types, date ranges)
- ✅ Default duration logic based on date range scope
- ✅ Recent highlights focus (last 48 hours to 30 days)
- ✅ Improved search with AI-powered query expansion
- ✅ Iterative filtering with AI-powered description analysis

## 2. Theory Engine API (services/theory-engine-api)

1. **Guardrails & Parsing**
   - `/api/highlights/plan` normalizes the inbound text and runs safety checks.
   - `parse_highlight_request` (OpenAI-assisted) maps the text into `HighlightRequestSpec` (sport, teams, date_range, duration, etc.).
2. **Search Planning**
   - Spec is converted to `SportsSearchSpec` inside `routers/highlights.py`.
   - `search_youtube_sports` generates multiple YouTube queries, widens publish windows, and fetches 200–250 candidates per request.
   - `calculate_highlight_score` ranks each candidate using highlight keywords, channel reputation, duration heuristics, and player/play-type matches.
3. **Filtering & Playlist Build**
   - `description_analyzer.py` (LLM) evaluates batched videos for relevance/quality.
   - `build_playlist_from_candidates` iteratively walks candidates, discarding low-confidence clips, backfilling until requested minutes hit, and tracking coverage notes.
4. **Caching & Persistence**
   - `PlaylistQuery` rows capture the normalized signature, metadata (sport, requested duration, etc.).
   - `Playlist` rows store the final ordered clips and explanation; subsequent identical queries hit cache unless stale.
5. **Responses & Logging**
   - Response payload includes playlist items, disclaimer, explanation (assumptions, filters, ranking factors, coverage notes).
   - Structured logs capture `query_text`, normalized signature, cache status, API call counts, request duration, and user id (or anonymous token).

### Recent Improvements

- ✅ Structured input eliminates ambiguity (sports, teams, players, play types explicitly captured)
- ✅ Default duration logic based on date range scope (single day = 60-90 min, decade = 8-10 hours)
- ✅ Aggressive recency defaults (last 7 days if no date specified)
- ✅ Stricter filtering for play-type specific queries (requires play type to be main focus)
- ✅ Enhanced logging with date window, publish lag, and rejection reasons

## 3. Supporting Packages

- `packages/py-core`: shared schemas (`HighlightRequestSpec`, `DateRange`, scoring utils) consumed by both FastAPI services.
- `packages/js-core`: TypeScript SDK (API client, hooks) used by the web app; today it only exports the free-form `planPlaylist` call.

### Gaps

- There is no shared type for a structured builder payload (sports[], players[], play_types[], explicit date range), so the contract stays text-centric.
- Because UX cannot collect structured filters, backend cannot lean into aggressive recency defaults without risking false assumptions.

## Summary of Improvements

1. ✅ **Structured Input** – Guided UI builder captures sports, teams, players, play types explicitly
2. ✅ **Recency Defaults** – Automatic "last 7 days" default when no date specified, with intelligent duration based on scope
3. ✅ **Enhanced Search** – AI-powered query expansion, multiple sport term variations, wider initial search
4. ✅ **Stricter Filtering** – AI-powered description analysis with play-type focus enforcement
5. ✅ **Better Observability** – Enhanced logging with date windows, publish lag, and rejection reasons

## Remaining Opportunities

- Further optimization of search query generation
- Additional metrics for builder usage patterns
- Performance improvements for large date ranges


