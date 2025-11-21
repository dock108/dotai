# Local Deployment and Testing Instructions

## Scope

**This guide covers local development and testing for the Sports Highlight Channel feature:**
- `services/theory-engine-api` - FastAPI backend service
- `apps/highlight-channel-web` - Next.js frontend application

**For full monorepo deployment (all services and apps), see `infra/DEPLOYMENT.md`.**

## Quick Start (TL;DR)

If you just want to get running quickly:

1. **Prerequisites**: PostgreSQL running, API keys configured
2. **Backend**: `cd services/theory-engine-api && uv sync && uv pip install -e ../../packages/py-core && alembic upgrade head && uv run uvicorn app.main:app --reload`
3. **Frontend**: `cd apps/highlight-channel-web && pnpm install && pnpm dev`
4. **Test**: Open http://localhost:3005 and try "NFL highlights from last night, 30 minutes"

For detailed setup, troubleshooting, and testing scenarios, continue reading below.

## Overview

This guide provides complete step-by-step instructions for setting up and testing the dock108 Sports Highlight Channel feature locally.

## Prerequisites Installation

### 1. Install Python 3.11+

**macOS (using Homebrew)**:
```bash
brew install python@3.11
python3.11 --version  # Verify installation
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

**Windows**:
- Download from python.org or use `pyenv-win`

### 2. Install uv (Python Package Manager)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv

# Verify
uv --version
```

### 3. Install Node.js 18+

**macOS (using Homebrew)**:
```bash
brew install node@18
node --version  # Verify
```

**Linux**:
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Or use nvm**:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

### 4. Install pnpm

```bash
npm install -g pnpm
pnpm --version  # Verify
```

### 5. Install PostgreSQL 14+

**macOS (using Homebrew)**:
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt install postgresql-14 postgresql-contrib
sudo systemctl start postgresql
```

**Windows**:
- Download from postgresql.org

**Verify PostgreSQL**:
```bash
psql --version
pg_isready  # Check if running
```

## Database Setup

### Option 1: Local PostgreSQL

```bash
# Simple: Create database (uses your current PostgreSQL user)
createdb dock108

# Or if you need to create a specific user first:
# Connect to PostgreSQL
psql postgres

# Inside psql prompt, run these SQL commands:
CREATE USER dock108 WITH PASSWORD 'changeme';
CREATE DATABASE dock108 OWNER dock108;
\q

# Note: Make sure to run CREATE USER and CREATE DATABASE inside the psql prompt,
# not as separate shell commands. After connecting with `psql postgres`, you'll
# see a `postgres=#` prompt where you can type SQL commands.
```

### Option 2: Docker PostgreSQL

```bash
docker run -d \
  --name dock108-postgres \
  -e POSTGRES_DB=dock108 \
  -e POSTGRES_USER=dock108 \
  -e POSTGRES_PASSWORD=changeme \
  -p 5432:5432 \
  postgres:14

# Verify it's running
docker ps | grep dock108-postgres
```

### Option 3: Docker Compose (if available)

```bash
cd infra
docker-compose up -d postgres
```

## API Keys Setup

### 1. Get YouTube Data API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "YouTube Data API v3"
4. Create credentials (API Key)
5. Copy the API key

### 2. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Navigate to API Keys
3. Create new secret key
4. Copy the key

## Backend Setup

### 1. Navigate to Service Directory

```bash
cd services/theory-engine-api
```

### 2. Create Environment File

```bash
# Copy example
cp ../../.env.example .env

# Edit .env with your values
nano .env  # or use your preferred editor
```

**Required `.env` contents**:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://dock108:changeme@localhost:5432/dock108

# API Keys
OPENAI_API_KEY=sk-your-openai-key-here
YOUTUBE_API_KEY=your-youtube-api-key-here

# Optional: YouTube OAuth (for playlist creation)
# YOUTUBE_OAUTH_ACCESS_TOKEN=your-oauth-token
# YOUTUBE_PLAYLIST_CHANNEL_ID=your-channel-id

# Environment
ENVIRONMENT=development
```

### 3. Install Python Dependencies

```bash
# Install uv if not already installed
pip install uv

# Sync dependencies (installs service dependencies)
uv sync

# Install py-core package (local monorepo dependency)
uv pip install -e ../../packages/py-core

# Verify installation
uv pip list | grep py-core
```

**Note**: The `py-core` package is a local monorepo dependency that must be installed separately. If you get `ModuleNotFoundError: No module named 'py_core'`, make sure you've run `uv pip install -e ../../packages/py-core` from the `services/theory-engine-api` directory.

### 4. Run Database Migrations

```bash
# From services/theory-engine-api directory
alembic upgrade head

# Verify tables were created
psql -d dock108 -c "\dt"
```

Expected tables: `playlist_queries`, `playlists`, `videos`, `customer_accounts`, `theories`, `evaluations`, `external_context_cache`

### 5. Start Backend Server

```bash
# Use uv run to ensure it uses the correct Python environment
uv run uvicorn app.main:app --reload --port 8000

# Alternative: If you want to use uvicorn directly, make sure you're in the uv environment
# uv sync creates a virtual environment - you can activate it with:
# source .venv/bin/activate  # On macOS/Linux
# Then: uvicorn app.main:app --reload --port 8000
```

**Verify backend is running**:
- Open http://localhost:8000/docs (FastAPI Swagger UI)
- Or: `curl http://localhost:8000/healthz` should return `{"status":"ok"}`

## Frontend Setup

### 1. Install Root Dependencies

```bash
# From repo root
pnpm install
```

This installs dependencies for all apps and packages in the monorepo.

### 2. Navigate to Frontend App

```bash
cd apps/highlight-channel-web
```

### 3. Create Environment File

```bash
# Create .env.local
echo "NEXT_PUBLIC_THEORY_ENGINE_URL=http://localhost:8000" > .env.local
```

### 4. Start Frontend Dev Server

```bash
pnpm dev
```

**Verify frontend is running**:
- Open http://localhost:3005
- Should see the highlight channel input form

## Testing Procedures

### 1. Backend Health Check

```bash
curl http://localhost:8000/healthz
```

Expected: `{"status":"ok"}`

### 2. Test Highlight Playlist Creation

```bash
curl -X POST http://localhost:8000/api/highlights/plan \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "NFL Week 12 highlights, 1 hour",
    "mode": "sports_highlight"
  }' | jq
```

**Expected Response**:
- `playlist_id` (integer)
- `query_id` (integer)
- `items` (array of video objects)
- `cache_status` ("fresh" for first request)
- `disclaimer` (legal disclaimer text)
- `total_duration_seconds` (integer)

**Save playlist_id for next test**:
```bash
PLAYLIST_ID=$(curl -s -X POST http://localhost:8000/api/highlights/plan \
  -H "Content-Type: application/json" \
  -d '{"query_text": "NFL Week 12 highlights, 1 hour", "mode": "sports_highlight"}' \
  | jq -r '.playlist_id')
echo $PLAYLIST_ID
```

### 3. Test Playlist Retrieval

```bash
curl http://localhost:8000/api/highlights/$PLAYLIST_ID | jq
```

Expected: Full playlist details with explanation, query_metadata, disclaimer

### 4. Test Cache Hit

```bash
# Same request should return cached result
curl -X POST http://localhost:8000/api/highlights/plan \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "NFL Week 12 highlights, 1 hour",
    "mode": "sports_highlight"
  }' | jq '.cache_status'
```

Expected: `"cached"`

### 5. Test Guardrails

**Copyright Violation Block**:
```bash
curl -X POST http://localhost:8000/api/highlights/plan \
  -H "Content-Type: application/json" \
  -d '{"query_text": "download full game", "mode": "sports_highlight"}'
```

Expected: `400 Bad Request` with error message

**YouTube Bypass Block**:
```bash
curl -X POST http://localhost:8000/api/highlights/plan \
  -H "Content-Type: application/json" \
  -d '{"query_text": "bypass youtube and download", "mode": "sports_highlight"}'
```

Expected: `400 Bad Request` with polite refusal

### 6. Test Metrics Endpoint

```bash
# JSON metrics
curl http://localhost:8000/api/highlights/metrics?days=7 | jq

# CSV metrics
curl http://localhost:8000/api/highlights/metrics/csv?days=7
```

Expected: Sports counts, average duration, cache statistics

### 7. Frontend Testing

1. **Load Homepage**: http://localhost:3005
   - Should show input form with preset chips

2. **Submit Query**: Enter "NFL Week 12 highlights, 1 hour"
   - Should show loading state
   - Should display playlist results

3. **View Explanation**: Click on explanation panel
   - Should show assumptions, filters, ranking factors

4. **Test Presets**: Click preset chips
   - Should auto-fill and submit queries

## Verification Checklist

- [ ] PostgreSQL is running and accessible
- [ ] Database migrations completed successfully
- [ ] Backend server starts without errors
- [ ] Health check endpoint returns `{"status":"ok"}`
- [ ] Frontend dev server starts without errors
- [ ] Frontend loads at http://localhost:3005
- [ ] Can create highlight playlist via API
- [ ] Can retrieve playlist details
- [ ] Cache hit works (same query returns cached)
- [ ] Guardrails block invalid requests
- [ ] Metrics endpoint returns data
- [ ] Frontend can submit queries and display results

## Troubleshooting

### Backend Won't Start

**Database Connection Error**:
```bash
# Check DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql+asyncpg://user:password@host:port/dbname

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

**Missing Dependencies**:
```bash
cd services/theory-engine-api
uv sync --verbose
```

**Port Already in Use**:
```bash
# Find process using port 8000
lsof -i :8000
# Kill process or use different port
uvicorn app.main:app --reload --port 8001
```

### Frontend Won't Start

**Port Already in Use**:
```bash
# Find process using port 3005
lsof -i :3005
# Or change port in package.json scripts
```

**Dependencies Not Installed**:
```bash
# From repo root
pnpm install
cd apps/highlight-channel-web
pnpm install
```

**Backend Not Running**:
- Ensure backend is running on http://localhost:8000
- Check `NEXT_PUBLIC_THEORY_ENGINE_URL` in `.env.local`

### API Errors

**YouTube API Quota Exceeded**:
- Check quota in Google Cloud Console
- Free tier: 10,000 units/day
- Each search = 100 units, video details = 1 unit

**OpenAI API Errors**:
- Verify API key is valid
- Check account has credits
- Ensure model access (`gpt-4o-mini`)

**Database Errors**:
```bash
# Check if tables exist
psql -d dock108 -c "\dt"

# Check migration status
cd services/theory-engine-api
alembic current

# Re-run migrations if needed
alembic upgrade head
```

### Cache Not Working

```bash
# Check if playlist_queries table has data
psql -d dock108 -c "SELECT COUNT(*) FROM playlist_queries;"

# Check normalized signatures
psql -d dock108 -c "SELECT normalized_signature, mode FROM playlist_queries LIMIT 5;"
```

## Logging and Monitoring

### View Backend Logs

```bash
# Pretty print JSON logs
uvicorn app.main:app --reload | jq

# Filter for highlight requests
uvicorn app.main:app --reload 2>&1 | grep highlight_playlist

# Save logs to file
uvicorn app.main:app --reload 2>&1 | tee backend.log
```

### View Frontend Logs

Check browser console (F12) or terminal where `pnpm dev` is running.

### Check Database

```bash
# Connect to database
psql -d dock108

# View recent queries
SELECT query_text, sport, created_at FROM playlist_queries ORDER BY created_at DESC LIMIT 10;

# View playlists
SELECT id, query_id, total_duration_seconds, created_at FROM playlists ORDER BY created_at DESC LIMIT 10;

# Check cache hit rate
SELECT 
  COUNT(DISTINCT q.normalized_signature) as total_queries,
  COUNT(DISTINCT p.id) as total_playlists,
  COUNT(DISTINCT q.normalized_signature) - COUNT(DISTINCT p.id) as estimated_cache_hits
FROM playlist_queries q
LEFT JOIN playlists p ON p.query_id = q.id;
```

## Theory Surfaces

All theory surfaces (bets, crypto, stocks, conspiracies) use the same backend API and can be tested similarly:

1. **Start backend** (if not already running):
   ```bash
   cd services/theory-engine-api
   uv run uvicorn app.main:app --reload
   ```

2. **Start any theory surface**:
   ```bash
   # Bets (port 3001)
   cd apps/theory-bets-web && pnpm dev

   # Crypto (port 3002)
   cd apps/theory-crypto-web && pnpm dev

   # Stocks (port 3003)
   cd apps/theory-stocks-web && pnpm dev

   # Conspiracies (port 3004)
   cd apps/theory-conspiracy-web && pnpm dev
   ```

3. **Test the surface**:
   - Open the app in browser
   - Enter a theory in the text area
   - Click "Evaluate Theory"
   - Review the response with domain-specific fields

See [`docs/THEORY_SURFACES.md`](THEORY_SURFACES.md) for detailed documentation.

## Data Workers

Data workers use Celery for async task processing:

1. **Start Redis** (if not already running):
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **Set environment variables**:
   ```bash
   export REDIS_URL=redis://localhost:6379/0
   export CELERY_BROKER_URL=redis://localhost:6379/0
   export CELERY_RESULT_BACKEND=redis://localhost:6379/0
   export YOUTUBE_API_KEY=your_key_here
   ```

3. **Start Celery worker**:
   ```bash
   cd services/data-workers
   uv sync
   uv run celery -A app.main worker --loglevel=info
   ```

4. **Start Celery beat** (for scheduled tasks):
   ```bash
   uv run celery -A app.main beat --loglevel=info
   ```

See [`services/data-workers/README.md`](../services/data-workers/README.md) for detailed documentation.

## Next Steps

After successful local setup:
1. Review `docs/HIGHLIGHTS_API.md` for API details
2. Review `docs/highlight-mvp.md` for constraints and limitations
3. Review `docs/THEORY_SURFACES.md` for theory surface documentation
4. See `infra/DEPLOYMENT.md` for full monorepo production deployment (all services and apps)

