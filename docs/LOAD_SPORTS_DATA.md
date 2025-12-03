# Loading Sports Data Through the Admin UI

> **Note**: This guide covers the sports data ingestion workflow. For general setup, see [`../README.md`](../README.md) and [`docs/START.md`](START.md).

## Prerequisites ✅
- ✅ PostgreSQL running (port 5432)
- ✅ Redis running (port 6379)  
- ✅ Backend API running (port 8000) - `dock108-theory-api`

## Step 1: Start the Frontend (theory-bets-web)

**Option A: Run in Docker**
```bash
cd infra
./docker-compose.sh up -d theory-bets-web
# Or: docker-compose --env-file ../.env -f docker-compose.yml up -d theory-bets-web
```

**Option B: Run Locally (Recommended for Development)**
```bash
cd apps/theory-bets-web
pnpm dev --port 3001
```

The frontend will be available at: **http://localhost:3001**

## Step 2: Start the Sports Scraper Celery Worker

The scraper worker processes the jobs queued from the admin UI. You need to run it separately:

**Option A: Run in Docker (Recommended)**
```bash
cd infra
./docker-compose.sh up -d scraper-worker
# Or: docker-compose --env-file ../.env -f docker-compose.yml up -d scraper-worker
```

**Option B: Run Locally (For Development)**
```bash
cd services/theory-bets-scraper
uv sync
uv run celery -A bets_scraper.celery_app.app worker --loglevel=info --queues=bets-scraper
```

**Note:** The scraper automatically reads from the root `.env` file (no need to manually set environment variables). Make sure your `.env` file has:
- `DATABASE_URL` (will be auto-converted from asyncpg to psycopg)
- `ODDS_API_KEY` (optional, for odds data)
- `REDIS_URL` (for Celery broker, defaults to `redis://localhost:6379/2`)

## Step 3: Access the Admin UI

1. Open your browser to: **http://localhost:3001/admin/theory-bets/ingestion**

2. You'll see a form to create scrape runs with:
   - **League** dropdown (NBA, NCAAB, NFL, NCAAF, MLB, NHL)
   - **Season** (optional, e.g., 2024)
   - **Start date** and **End date** (optional)
   - **Include Boxscores** checkbox
   - **Include Odds** checkbox

## Step 4: Create Your First Scrape Run

Example: Scrape NBA games from the last week

1. Select **League**: NBA
2. Leave **Season** empty (or enter current season like 2024)
3. Set **Start date** to 7 days ago
4. Set **End date** to today
5. Check both **Include Boxscores** and **Include Odds**
6. Click **Schedule Run**

The run will be created and queued. The Celery worker will pick it up and start processing.

## Step 5: Monitor Progress

- **On the ingestion page**: See all scrape runs with their status (pending, running, success, error)
- **Click a run ID**: View detailed information about the run
- **Check worker logs**: See real-time progress in the Celery worker terminal

## Step 6: View Ingested Data

Once a run completes successfully:

1. Go to: **http://localhost:3001/admin/boxscores**
2. Filter by league, date range, etc.
3. Click on any game to see detailed boxscore, player stats, and odds data

## Troubleshooting

### Force-refresh cached scoreboard pages

The scrapers keep a local HTML cache under `services/theory-bets-scraper/game_data` so we do not hammer Sports Reference. When re-running the same date range, set either of these env vars before starting the worker to override the defaults:

- `SCRAPER_HTML_CACHE_DIR=/tmp/my-fresh-cache` — points the cache at a new directory.
- `SCRAPER_FORCE_CACHE_REFRESH=true` — ignores whatever is already cached and refetches from the network while still writing updated files.

Both shortcuts map to the nested scraper config automatically, so you do **not** need to use `SCRAPER_CONFIG__...` syntax anymore. The worker logs now emit `cache_hit` / `cache_refresh_forced` events so you can confirm which path was taken.

**"Failed to enqueue scrape job" error:**
- Make sure the Celery worker is running
- Check that Redis is accessible and password is correct
- Verify `REDIS_PASSWORD` and `CELERY_BROKER_URL` in your `.env`
- Ensure you're using `./docker-compose.sh` or `--env-file ../.env` when starting services

**Worker not picking up jobs:**
- Check the worker is listening to the `bets-scraper` queue
- Verify Redis connection: `redis-cli ping` (should return PONG)
- Check worker logs for errors

**No data appearing:**
- Wait for the scrape run to complete (check status on ingestion page)
- Verify the date range has games (some leagues are seasonal)
- Check worker logs for scraping errors

## Quick Start Commands

```bash
# Terminal 1: Start infrastructure and backend
cd infra
./docker-compose.sh up -d postgres redis theory-engine-api scraper-worker
# Or: docker-compose --env-file ../.env -f docker-compose.yml up -d postgres redis theory-engine-api scraper-worker

# Terminal 2: Start frontend
cd apps/theory-bets-web && pnpm dev --port 3001

# Then open: http://localhost:3001/admin/theory-bets/ingestion
```

**Or run scraper worker locally (for development):**
```bash
# Terminal 2: Start scraper worker (local development)
cd services/theory-bets-scraper
uv sync
uv run celery -A bets_scraper.celery_app.app worker --loglevel=info --queues=bets-scraper
```

## NCAAB End-to-End Smoke Test

1. Export any cache overrides you need (see troubleshooting section) and confirm `ODDS_API_KEY` is set.
2. Start Postgres/Redis/API as described above plus the scraper worker.
3. From the admin ingestion UI, enqueue an NCAAB run covering **2024-11-01 → 2024-11-07** with both *Include Boxscores* and *Include Odds* checked.
4. Watch the worker logs; you should see:
   - `cache_hit` or `cache_refresh_forced` events per day.
   - `ncaab_fetch_games_start` and `ncaab_fetch_games_complete` events showing games parsed per day.
   - `persist_game_payload` entries for each boxscore.
   - `historical_day_complete` + `odds_persist_skipped` summaries with non-zero insert counts.
5. When the run finishes, validate data:
   - `SELECT COUNT(*) FROM sports_game WHERE league_id = (SELECT id FROM sports_league WHERE code='NCAAB');`
   - `SELECT COUNT(*) FROM sports_game_odds WHERE league_id = (SELECT id FROM sports_league WHERE code='NCAAB');`
6. Re-run the same window with `SCRAPER_FORCE_CACHE_REFRESH=true` to confirm cached HTML can be bypassed when you need fresh pages.

If any of the checks fail, capture the Celery log output along with the `services/theory-bets-scraper/game_data` folder contents for debugging.

## NCAAB Team Matching Notes

**Important**: NCAAB uses **full team name matching only** (no abbreviations) due to the large number of teams (350+) which causes abbreviation collisions. For example, "UR" could refer to both UTSA Roadrunners and UNLV Rebels. 

- Team abbreviations are set to `NULL` for NCAAB teams in the database
- Odds matching relies on full team names rather than abbreviations
- This ensures accurate team matching when linking odds data to games

Other leagues (NBA, NFL, MLB, NHL) continue to use abbreviations for team matching.

