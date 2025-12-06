# dock108 Monorepo

AI-powered theory evaluation platform for sports betting, crypto, stocks, and more. One Python backend, multiple Next.js frontends, shared components.

## What's Here

```
apps/                      # Next.js frontends
  theory-bets-web/         # Sports betting theory evaluation (port 3001)
  theory-crypto-web/       # Crypto strategy interpreter (port 3002)
  theory-stocks-web/       # Stock analysis (port 3003)
  conspiracy-web/          # Conspiracy fact-checking (port 3004)
  highlights-web/          # Sports highlight playlist generator (port 3005)
  dock108-web/             # Landing portal (port 3000)

services/                  # Python backends
  theory-engine-api/       # FastAPI - all theory domains, highlights, admin (port 8000)
  theory-bets-scraper/     # Celery workers - sports data ingestion

packages/                  # Shared libraries
  py-core/                 # Python schemas, guardrails, scoring
  js-core/                 # TypeScript SDK, React hooks, API client
  ui/                      # Shared UI components (DockHeader, DockFooter)
  ui-kit/                  # Domain components (TheoryForm, TheoryCard)

infra/                     # Docker Compose, Traefik config
docs/                      # Documentation
```

## Quick Start

### Prerequisites
- Python 3.11+ with `uv`
- Node.js 18+ with `pnpm`
- Docker and Docker Compose
- API keys: OpenAI, YouTube Data API (optional: Odds API)

### 1. Setup

```bash
git clone <repo-url> && cd dock108
cp .env.example .env
# Edit .env with your API keys and passwords
```

### 2. Start Infrastructure

```bash
# From repo root - uses Makefile to ensure .env is loaded
make up
```

Or manually:
```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d
```

### 3. Run Migrations

```bash
cd services/theory-engine-api
uv sync && uv pip install -e ../../packages/py-core
alembic upgrade head
```

### 4. Start Development

```bash
# Backend (in services/theory-engine-api)
uv run uvicorn app.main:app --reload --port 8000

# Frontend (in apps/theory-bets-web or any app)
pnpm install && pnpm dev
```

## Key Features

### Theory Bets v1 Pipeline
Users submit betting theories → LLM grades prompt and infers config → historical performance analysis (2 seasons) → 30-day backtest → Monte Carlo for upcoming bets → Kelly sizing and P2P pricing → results page with recommendations.

**User flow:** `/` → submit theory → redirect to `/theory/{run_id}`
**Admin flow:** `/admin/theory-bets/runs` → browse/filter runs → click through to results

### EDA / Modeling Lab (admin)
- Generate features from selected stats and context (rest/rolling), run correlation analysis, and build lightweight models.
- Preview the feature matrix and data quality (null/non-numeric counts) before analysis; download the raw matrix as CSV from Step 1.
- Results card links to the exact game sample in `/admin/theory-bets/games` and provides a CSV export of the feature matrix (opens in a new tab).
- Cleaning toggles for analysis/model: drop rows with missing/non-numeric features or enforce a minimum number of non-null features.
- Endpoints: `POST /api/admin/sports/eda/generate-features`, `POST /api/admin/sports/eda/preview` (CSV/JSON), `POST /api/admin/sports/eda/analyze`, `POST /api/admin/sports/eda/build-model`, `POST /api/admin/sports/eda/analyze/export` (CSV).

### Sports Data Ingestion
Celery workers scrape boxscores and odds for NBA, NFL, MLB, NHL, NCAAB, NCAAF. Admin UI at `/admin/theory-bets/ingestion` to trigger and monitor runs.

### Sports Highlights
Natural language requests → AI parsing → YouTube search with channel reputation scoring → intelligent caching → embedded player with 48-hour watch tokens.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/theory-runs` | Submit theory for v1 evaluation |
| `GET /api/theory-runs/{id}` | Get evaluation results |
| `GET /api/admin/theory-runs` | List all runs (admin) |
| `POST /api/highlights/plan` | Plan highlight playlist |
| `GET /api/admin/sports/games` | Browse games data |
| `POST /api/admin/sports/scraper/runs` | Trigger scrape run |
| `POST /api/admin/sports/eda/generate-features` | Generate derived features for EDA |
| `POST /api/admin/sports/eda/preview` | Preview feature matrix (CSV) or data quality JSON |
| `POST /api/admin/sports/eda/analyze` | Run correlation analysis for selected features/target |
| `POST /api/admin/sports/eda/build-model` | Train lightweight model on feature matrix |
| `POST /api/admin/sports/eda/analyze/export` | Export feature matrix + targets as CSV |

Full API docs at `http://localhost:8000/docs` when backend is running.

## Environment Variables

All config in root `.env` file (single source of truth):

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dock108
OPENAI_API_KEY=sk-...

# For highlights
YOUTUBE_API_KEY=AIza...

# For sports odds
ODDS_API_KEY=...

# Infrastructure
REDIS_PASSWORD=...
POSTGRES_PASSWORD=...
```

## Documentation

- **[`docs/START.md`](docs/START.md)** - Quick start guide
- **[`docs/LOCAL_DEPLOY.md`](docs/LOCAL_DEPLOY.md)** - Detailed local setup
- **[`docs/THEORY_SURFACES.md`](docs/THEORY_SURFACES.md)** - Theory surfaces design
- **[`docs/UNIFIED_THEORY_BETS.md`](docs/UNIFIED_THEORY_BETS.md)** - v1 pipeline details
- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** - System architecture
- **[`docs/ROADMAP.md`](docs/ROADMAP.md)** - Project roadmap

## Development Commands

```bash
# Docker (from repo root)
make up              # Start all services
make down            # Stop all services
make logs            # View all logs
make logs-svc SVC=theory-api  # View specific service logs

# Frontend (from app directory)
pnpm dev             # Start dev server
pnpm build           # Production build
pnpm lint            # Run linter

# Backend (from services/theory-engine-api)
uv run uvicorn app.main:app --reload  # Dev server
alembic upgrade head                   # Run migrations
alembic revision --autogenerate -m "description"  # New migration
```

## Project Status

**Working:**
- All theory evaluation surfaces (bets, crypto, stocks, conspiracies)
- Theory bets v1 pipeline with LLM grading and historical analysis
- Sports data ingestion for 6 leagues
- Sports highlights playlist generator
- Admin UI for data management and run tracing

**In Progress:**
- Real filters for theory matching (back-to-back, altitude)
- Enhanced Monte Carlo with trained models
- Admin UI styling improvements

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for full roadmap.
