# Loading Sports Data Through the Admin UI

> **Note**: This guide covers the sports data ingestion workflow. For general setup, see [`README.md`](README.md) and [`START.md`](START.md).

## Prerequisites ✅
- ✅ PostgreSQL running (port 5432)
- ✅ Redis running (port 6379)  
- ✅ Backend API running (port 8000) - `dock108-theory-api`

## Step 1: Start the Frontend (theory-bets-web)

**Option A: Run in Docker**
```bash
cd infra
./docker-compose.sh up -d theory-bets-web
```

**Option B: Run Locally (Recommended for Development)**
```bash
cd apps/theory-bets-web
pnpm dev --port 3001
```

The frontend will be available at: **http://localhost:3001**

## Step 2: Start the Sports Scraper Celery Worker

The scraper worker processes the jobs queued from the admin UI. You need to run it separately:

```bash
cd services/theory-bets-scraper
uv run celery -A bets_scraper.celery_app.app worker --loglevel=info --queues=bets-scraper
```

**Important:** Make sure your `.env` file in the root has:
- `DATABASE_URL` (will be auto-converted from async to sync)
- `ODDS_API_KEY` (your Odds API key)
- `REDIS_URL` (for Celery broker)

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

**"Failed to enqueue scrape job" error:**
- Make sure the Celery worker is running
- Check that Redis is accessible
- Verify `CELERY_BROKER_URL` in your `.env`

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
# Terminal 1: Start frontend
cd apps/theory-bets-web && pnpm dev --port 3001

# Terminal 2: Start scraper worker
cd services/theory-bets-scraper && uv run celery -A bets_scraper.celery_app.app worker --loglevel=info --queues=bets-scraper

# Then open: http://localhost:3001/admin/theory-bets/ingestion
```

