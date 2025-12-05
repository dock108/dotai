# Backend Services Documentation

This directory contains documentation for backend services in the dock108 monorepo.

## Services

| Service | Port | Description |
|---------|------|-------------|
| `theory-engine-api` | 8000 | FastAPI backend (theory evaluation, highlights, admin) |
| `theory-bets-scraper` | N/A | Celery workers for sports data ingestion |

## Documentation

- **[`theory-engine-api.md`](theory-engine-api.md)** - FastAPI backend service documentation

## Quick Start

See the main **[`../LOCAL_DEPLOY.md`](../LOCAL_DEPLOY.md)** for development setup.

### Start Theory Engine API

```bash
cd services/theory-engine-api
uv sync
uv pip install -e ../../packages/py-core
alembic upgrade head
uv run uvicorn app.main:app --reload
```

### Start Scraper Workers (via Docker)

```bash
cd infra
./docker-compose.sh up -d scraper-worker
```
