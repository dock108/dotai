## Admin Utilities Template

This document describes the current **admin utilities** for the sports betting (theory-bets) engine and provides a **template and concrete plan** for implementing parallel admin utilities for the **crypto** and **stocks** engines.

Use this as the canonical guide for:
- What the admin layer supports today
- How it is wired end-to-end (API ↔ worker ↔ frontend)
- How to scaffold and adapt the same patterns for other engines

---

## 1. Conceptual Overview

### 1.1 Goals of the Admin Utilities

- **Operational control**: Schedule, monitor, and backfill ingestion/scraping runs.
- **Data inspection**: Browse and drill into the normalized data the engines produce (games, teams, odds for sports; assets, candles, events for markets; strategies, backtests, alerts for engines).
- **Debugging support**: Surface run status, errors, and metadata to help diagnose issues without digging into logs.
- **Engine-agnostic pattern**: Provide a common scaffold so adding new domains (sports, crypto, stocks, etc.) is straightforward.

### 1.2 High-Level Architecture

- **Backend API (`theory-engine-api`)**
  - Exposes admin endpoints under `api/admin/...` (sports today; crypto/stocks next).
  - Owns database models (`db_models.py`) and Pydantic schemas.
  - Sends jobs to background workers via Celery.
  - Normalizes engine data into stable, queryable tables.

- **Workers (e.g., `theory-bets-scraper`)**
  - Long-running ingestors/scrapers.
  - Implement league/sport/asset-specific scraping or data ingestion logic.
  - Persist normalized payloads via shared ORM & persistence helpers.

- **Admin Frontend (`theory-bets-web`)**
  - Next.js app with admin routes under `/admin/...`.
  - Uses light-theme, card-based UI components for runs & data browsing.
  - Talks to `theory-engine-api` via `NEXT_PUBLIC_THEORY_ENGINE_URL`.

The key design choice is that **each engine** (bets, crypto, stocks) should:
- Reuse the **same admin UX patterns**.
- Reuse the **same service boundaries** (API ↔ worker).
- Change only the **domain-specific types, filters, and pages**.

---

## 2. Current Sports Admin Capabilities (theory-bets)

This section documents what the bets admin supports today.

### 2.1 Backend Data Model & API

**Core models (sports):**
- `SportsLeague` — leagues such as `NBA`, `NFL`, `NCAAF`, `NCAAB`, `MLB`, `NHL`.
- `SportsTeam` — normalized teams per league, with external codes for mapping.
- `SportsGame` — single sporting event; includes:
  - League, season, season type, date/time
  - Home/away teams, scores, status
  - Venue, source key (Sports Reference), external IDs
- `SportsTeamBoxscore` — team-level stats per game.
- `SportsPlayerBoxscore` — player-level stats per game.
- `SportsGameOdds` — odds snapshots (lines, totals, spreads, etc.) from The Odds API.
- `SportsScrapeRun` — ingestion/scraping runs; tracks:
  - League, season, date range
  - Flags: include boxscores, include odds, backfill player stats, backfill odds
  - Status, timestamps, summary/error details, Celery job ID

**Admin API (sports):**
- **Scrape runs**
  - `GET /api/admin/sports/scraper/runs` — list recent runs.
  - `GET /api/admin/sports/scraper/runs/{runId}` — run details, config, status.
  - `POST /api/admin/sports/scraper/runs` — create/schedule a new run:
    - Body contains:
      - `leagueCode` (`NBA`, `NCAAB`, `NFL`, `NCAAF`, `MLB`, `NHL`)
      - `season` (year)
      - `startDate`, `endDate` (dates; auto-filled from season if blank)
      - Flags: include/exclude boxscores and odds; backfill flags
      - `requestedBy`
    - Persists a `SportsScrapeRun` row and fires a Celery task (`run_scrape_job`).

- **Data browsing**
  - `GET /api/admin/sports/leagues` — list supported leagues.
  - `GET /api/admin/sports/teams` — list teams (with filters by league).
  - `GET /api/admin/sports/teams/{id}` — team detail; related games.
  - `GET /api/admin/sports/games` — list games (filters: league, date range, season).
  - `GET /api/admin/sports/games/{id}` — game detail:
    - Game identity (teams, scores, metadata)
    - Team stats (from `stats` JSONB on `SportsTeamBoxscore`)
    - Player stats (flattened from `stats` JSONB on `SportsPlayerBoxscore`)
    - Odds snapshots (from `SportsGameOdds`)

**Worker routing:**
- API `POST` creates a `SportsScrapeRun`.
- API enqueues Celery task `run_scrape_job` with:
  - `run_id`
  - JSON-encoded `IngestionConfig` (league, season, date range, flags).
- Worker (`theory-bets-scraper`) uses `ScrapeRunManager.run()` to:
  - Select the correct scraper based on `leagueCode` (NBA, NCAAB, NFL, NCAAF, MLB, NHL).
  - Stream through dates → fetch/normalize games → persist to DB.
  - Run odds sync via `OddsSynchronizer` for the date range.
  - Optionally backfill missing player stats and/or odds.

### 2.2 Scraper & Odds Engines

**Scrapers (Sports Reference family):**
- Base class: `BaseSportsReferenceScraper`
  - Shared HTTP client & headers.
  - **HTML caching** to disk by league/season/game.
  - **Polite delays** (randomized between requests, backoff on 429).
  - `fetch_games_for_date(day: date) → list[NormalizedGame]`.
  - `fetch_single_boxscore(source_game_key, game_date)` for backfill.

- Implementations:
  - `NBASportsReferenceScraper` — Basketball Reference.
  - `NCAABSportsReferenceScraper` — `sports-reference.com/cbb`.
  - `NFLSportsReferenceScraper` — `pro-football-reference.com`.
  - `NCAAFSportsReferenceScraper` — `sports-reference.com/cfb`.
  - `MLBSportsReferenceScraper` — `baseball-reference.com`.
  - `NHLSportsReferenceScraper` — `hockey-reference.com`.

**Odds (The Odds API):**
- `OddsAPIClient`
  - Live and historical odds (`v4` API).
  - JSON caching per API request to save credits.
  - Normalization into `NormalizedOddsSnapshot` objects.
- `OddsSynchronizer`
  - `sync(config)` — sync odds for a date range and league.
  - `sync_single_date(league_code, date)` — targeted backfill per day.
  - Resolves teams/games from the DB and upserts `SportsGameOdds`.

### 2.3 Admin Frontend (theory-bets-web)

**Routing & layout:**
- Root admin layout: `/admin/layout.tsx`
  - Light theme, sidebar nav (`AdminNav`).
  - Main content area with appropriate margins below the main site header.

- Key routes:
  - `/admin/theory-bets` — bets admin dashboard (high-level overview & quick links).
  - `/admin/theory-bets/ingestion` — list of scrape runs.
  - `/admin/theory-bets/ingestion/[runId]` — run details.
  - `/admin/theory-bets/teams` — teams browser.
  - `/admin/theory-bets/teams/[id]` — team detail.
  - `/admin/games` — games list (legacy path).
  - `/admin/games/[id]` — game detail (full boxscore and odds).

**Ingestion page behavior:**
- Form fields:
  - League (select), Season (year), Start/End Date, flags, `requestedBy`.
- UX rules:
  - If **season is set** and **dates are blank**, `getFullSeasonDates` is used to auto-fill a sensible season range per league (including playoffs + buffers).
  - Date fields are treated as required *for the run*, but auto-filled for the user based on season.
- On submit:
  - Calls `POST /api/admin/sports/scraper/runs`.
  - Displays 422/500 errors inline.
  - Shows updated run list with status badges.

**Detail pages:**
- **Run detail**: Shows:
  - Config (league, season, date range, flags).
  - Status timeline (pending → running → success/error).
  - Summary string (games scraped, odds synced, backfills).
- **Game detail**: Shows:
  - Teams, final score, date/time, league/season.
  - Team stats table (team-level).
  - Player stats tables (rows per player, derived from `stats` JSONB).
  - Odds table (book, market, open/close lines, etc.).

---

## 3. Template for Other Engines (Crypto & Stocks)

This section defines the **admin utilities template** and a **concrete adaptation plan** for **crypto** and **stocks**.

### 3.1 Shared Admin Pattern

For each engine (sports, crypto, stocks), we want the same pattern:

1. **Domain models in DB**
   - Core entities (games/assets, prices, signals, strategies, runs).
   - Normalized, engine-agnostic, with JSONB for schema-flexible stats.

2. **Admin API surface**
   - `/api/admin/{domain}/ingestion/runs` — schedule & inspect ingestion runs.
   - `/api/admin/{domain}/entities` — browse key entities (games, assets, strategies, etc.).
   - `/api/admin/{domain}/entities/[id]` — detail views.

3. **Workers / engines**
   - Dedicated workers per domain:
     - `theory-bets-scraper` (sports).
     - `theory-crypto-worker` (crypto).
     - `theory-stocks-worker` (equities).
   - Each worker:
     - Accepts a unified `IngestionConfig`-style payload.
     - Encapsulates external API/feeds and normalization.
     - Persists via shared ORM models.

4. **Admin frontend**
   - Single Next.js admin shell (`/admin/...`) with **namespaced sections**:
     - `/admin/theory-bets/...`
     - `/admin/theory-crypto/...`
     - `/admin/theory-stocks/...`
   - Shared UI components for:
     - Run tables, filters, status badges.
     - Detail cards (config, summary, errors).
     - Data tables (assets, games, strategies, etc.).

---

## 4. Crypto Admin Utility – Implementation Plan

This section is a **concrete plan** for building a crypto admin util that mirrors the sports admin.

### 4.1 Backend: Data Model

Add crypto-specific models (in `db_models.py` or a crypto-specific module):

- `CryptoExchange`
  - `id`, `code` (e.g., `BINANCE`, `COINBASE`), `name`, metadata JSONB.
- `CryptoAsset`
  - `id`, `symbol` (`BTC`, `ETH`), `base`, `quote`, `exchange_id`, `external_codes` JSONB.
- `CryptoCandle`
  - `id`, `asset_id`, `exchange_id`, `timeframe` (1m, 5m, 1h, 1d), ts, open/high/low/close, volume.
- `CryptoIngestionRun`
  - Fields analogous to `SportsScrapeRun`:
    - `exchange_code`, `symbol`, `timeframe`, date/time range, flags (include candles, include orderbook, etc.), status, job_id, config JSONB, summary/error.
- (Optionally) `CryptoSignal`, `CryptoStrategyRun`, `CryptoAlert` for higher-level engine features.

Use JSONB (`stats`-like) for flexible fields:
- Per-candle metadata (VWAP, trade count, etc.).
- Per-run configuration snapshots.

### 4.2 Backend: Admin API – Crypto

Create a crypto admin router, e.g.:
- `app/routers/crypto_data.py`

Endpoints:
- **Runs**
  - `GET /api/admin/crypto/ingestion/runs`
  - `GET /api/admin/crypto/ingestion/runs/{runId}`
  - `POST /api/admin/crypto/ingestion/runs`
    - Request model `CryptoIngestionConfig` (similar to `IngestionConfig`):
      - `exchangeCode` (enum).
      - `symbols: string[]` or single `symbol`.
      - `timeframe` (1m/5m/1h/1d).
      - `start`, `end` (ISO datetimes).
      - Flags: `includeCandles`, `includeOrderbook`, `backfillMissingCandles`, etc.

- **Data browsing**
  - `GET /api/admin/crypto/assets` — list assets (filters: exchange, symbol).
  - `GET /api/admin/crypto/assets/{id}` — asset detail: recent candles, runs.
  - `GET /api/admin/crypto/candles` — list candles (filters: symbol, exchange, timeframe, date range).
  - `GET /api/admin/crypto/candles/{id}` — single candle detail (mainly for debugging).

Behavior:
- On `POST /ingestion/runs`:
  - Create `CryptoIngestionRun` row.
  - Send Celery task `run_crypto_ingestion_job` with `run_id` + config JSON.

### 4.3 Worker: Crypto Ingestion

Create `theory-crypto-worker` service:
- Dockerized similarly to `theory-bets-scraper`, sharing:
  - `py-core` types.
  - `theory-engine-api` models.

Core entrypoint:
- `CryptoIngestionRunManager.run(run_id: int, config: CryptoIngestionConfig)`
  - Similar to `ScrapeRunManager` for sports.
  - Responsibilities:
    - Mark run `running` → `success`/`error`.
    - Iterate over requested time ranges and assets.
    - Call external data providers (e.g., exchange REST/WebSocket or a unified crypto data API).
    - Normalize candles into `CryptoCandle` records.
    - Optionally perform **backfill** for gaps (missing candles).
    - Aggregate summary metrics (candles inserted, gaps backfilled) and persist in run `summary`.

Best practices:
- Rate limiting & polite usage (backoff strategies).
- Local caching (JSON per response) similar to sports HTML caching.
- Clear error logging with context (`exchange`, `symbol`, `timeframe`, `ts`).

### 4.4 Frontend: Crypto Admin Pages

Under `theory-bets-web` (or a shared admin app), add:

- Navigation:
  - Extend `AdminNav` to add:
    - `Crypto` section → `/admin/theory-crypto`.

- Routes:
  - `/admin/theory-crypto` — dashboard:
    - Panels: recent runs, top assets by volume, data coverage status.
  - `/admin/theory-crypto/ingestion` — crypto ingestion runs:
    - Form:
      - Exchange, symbol(s), timeframe, start/end, flags.
    - Run table matching the sports ingestion page (status, summary, created at).
  - `/admin/theory-crypto/ingestion/[runId]` — run detail:
    - Run config & status timeline.
    - Summary: candles ingested, gaps filled, error counts.
  - `/admin/theory-crypto/assets` — asset browser:
    - Filters: exchange, symbol prefix, market (spot/perp).
  - `/admin/theory-crypto/assets/[assetId]` — asset detail:
    - Metadata card (exchanges, base/quote).
    - Recent candles chart (basic OHLC).
    - Recent runs that touched this asset.

Reuse components:
- The **run list** and **run detail** UI can be almost identical to sports with:
  - Different columns (exchange, symbol, timeframe vs league/season/dates).
  - Minor text changes (e.g., “Candles” vs “Games & Odds”).

---

## 5. Stocks Admin Utility – Implementation Plan

The stocks admin is structurally similar to crypto but with equities/indices.

### 5.1 Backend: Data Model

Add stocks-specific models:

- `EquityExchange`
  - `id`, `code` (`NYSE`, `NASDAQ`), `name`, `timezone`, metadata JSONB.
- `EquityAsset`
  - `id`, `ticker` (e.g., `AAPL`), `name`, `exchange_id`, `sector`, `industry`, `external_codes` JSONB.
- `EquityCandle`
  - `id`, `asset_id`, `timeframe` (1m/5m/1d), ts, OHLC, volume.
- `EquityCorporateAction` (optional)
  - Splits, dividends, etc., normalizing feed data.
- `EquityIngestionRun`
  - Analogous to `SportsScrapeRun` / `CryptoIngestionRun`:
    - `exchangeCode`, `tickers` (list/string), `timeframe`, `start`, `end`, flags, `status`, `job_id`, `summary`, `config` JSONB.

### 5.2 Backend: Admin API – Stocks

Create a stocks admin router, e.g.:
- `app/routers/stocks_data.py`

Endpoints:
- **Runs**
  - `GET /api/admin/stocks/ingestion/runs`
  - `GET /api/admin/stocks/ingestion/runs/{runId}`
  - `POST /api/admin/stocks/ingestion/runs`
    - Request model `StocksIngestionConfig`:
      - `exchangeCode`
      - `tickers` (string or string array)
      - `timeframe` (1m/5m/1d)
      - `start`, `end`
      - Flags: `includeCandles`, `includeFundamentals`, `backfillMissingCandles`, etc.

- **Data browsing**
  - `GET /api/admin/stocks/assets` — list equities (filters: exchange, sector, ticker).
  - `GET /api/admin/stocks/assets/{id}` — equity detail.
  - `GET /api/admin/stocks/candles` — list candles (filters: ticker, timeframe, date range).
  - `GET /api/admin/stocks/candles/{id}` — single candle detail.

### 5.3 Worker: Stocks Ingestion

Create `theory-stocks-worker` service:

- `StocksIngestionRunManager.run(run_id, config: StocksIngestionConfig)`
  - Similar responsibilities to Crypto & Sports:
    - Validate config and tickers.
    - Call stocks data provider (e.g., paid market data API).
    - Normalize results into `EquityCandle` and optional `EquityCorporateAction`.
    - Handle **backfills** for missing candles.
    - Persist run summary and error details.

Rate limits & caching:
- Mirror crypto & sports:
  - Cache JSON responses by asset/timeframe/date bucketing.
  - Implement retry/backoff around provider rate limits.

### 5.4 Frontend: Stocks Admin Pages

Add stocks pages to the admin shell:

- Navigation:
  - Extend `AdminNav` to add:
    - `Stocks` section → `/admin/theory-stocks`.

- Routes:
  - `/admin/theory-stocks` — stocks dashboard:
    - Quick stats: number of assets, coverage by exchange/timeframe.
    - Recent ingestion runs and alerts.
  - `/admin/theory-stocks/ingestion` — ingestion runs:
    - Form:
      - Exchange, tickers, timeframe, start/end, flags.
    - Run table identical pattern to sports/crypto.
  - `/admin/theory-stocks/ingestion/[runId]` — run detail:
    - Config, status, summary (candles loaded, coverage %, gaps).
  - `/admin/theory-stocks/assets` — equities browser:
    - Filters: exchange, sector, ticker prefix.
  - `/admin/theory-stocks/assets/[assetId]` — equity detail:
    - Metadata (name, sector, industry).
    - Recent candles chart.
    - Related ingestion runs.

Leverage shared components:
- Reuse tables, filters, status chips from sports & crypto.
- Abstract a generic `<AdminRunList domain=\"bets\" | \"crypto\" | \"stocks\">` if desired.

---

## 6. Practical Adaptation Checklist

Use this checklist when bringing up a new admin domain (e.g., crypto or stocks):

1. **DB & Models**
   - [ ] Define domain models (`*Asset`, `*Candle`, `*IngestionRun`, etc.) in `db_models.py`.
   - [ ] Apply migrations and ensure constraints/indices match expected query patterns.
   - [ ] Use JSONB for flexible stats/metadata where schema is not fixed.

2. **Ingestion Run Schema**
   - [ ] Define `*IngestionConfig` Pydantic model (similar to `IngestionConfig` for sports).
   - [ ] Map it to a `*IngestionRun` ORM table with:
     - Config JSONB, status, job_id, summary, timestamps.

3. **Admin API Router**
   - [ ] Create `/api/admin/{domain}/ingestion/runs` endpoints (GET list, GET by ID, POST).
   - [ ] Create list/detail endpoints for key entities (`assets`, `candles`, `games`, etc.).

4. **Worker**
   - [ ] Create `{Domain}IngestionRunManager` with a `run(run_id, config)` entrypoint.
   - [ ] Wire Celery task (`run_{domain}_ingestion_job`) and ensure queues are configured.
   - [ ] Implement:
     - Main ingestion path.
     - Optional **backfill** behavior for missing data.
     - Summary logging and DB updates for run status.

5. **Frontend**
   - [ ] Add navigation entry in `AdminNav` for the new domain.
   - [ ] Implement:
     - Dashboard page (overview).
     - Ingestion list & detail pages.
     - Entity browser & detail pages (assets/games/etc.).
   - [ ] Reuse sports admin components wherever possible (forms, tables, cards).

6. **Config & Env**
   - [ ] Ensure domain-specific API keys/URLs are in root `.env`.
   - [ ] Thread env vars through Docker Compose and Dockerfiles to:
     - API container.
     - Worker container(s).
     - Frontend (only if needed as `NEXT_PUBLIC_*`).

7. **Testing**
   - [ ] Run a small ingestion run (narrow date range / single symbol or ticker).
   - [ ] Check DB contents (sanity check).
   - [ ] Verify admin UI surfaces:
     - Run is created.
     - Status moves through pending → running → success/error.
     - Data appears in entity browsers and detail pages.

---

## 7. How to Use This Template

- When adding a new domain (e.g., **options**, **FX**, or a new sports data source**):
  - Start by cloning the **sports admin pattern**:
    - DB schema → ingestion run model → API → worker → admin pages.
  - Use the **Crypto** and **Stocks** sections above as starting points for:
    - Naming, field choices, and endpoint shapes.
  - Keep all admin utilities:
    - Light-themed.
    - Focused on **operational clarity** (statuses, counts, errors).
    - Consistent across domains so any operator can hop between bets, crypto, and stocks without relearning the UI.

This file should remain the **single source of truth** for how admin utilities are designed, what they support, and how to extend them for new engines.
