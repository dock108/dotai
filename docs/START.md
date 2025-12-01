# Step-by-Step Startup Guide

> **Note**: This is a quick Docker-focused startup guide. For comprehensive setup instructions, see [`README.md`](README.md) and [`docs/LOCAL_DEPLOY.md`](docs/LOCAL_DEPLOY.md).

## Prerequisites
- Docker Desktop is running
- All ports are free (8000, 5432, 6379, 3000-3005)

**Note:** If you have local PostgreSQL or Redis running, stop them first:
```bash
# Stop via Homebrew services (if installed via brew)
brew services stop postgresql
brew services stop redis

# Or kill processes directly
lsof -ti:5432 | xargs kill -9  # PostgreSQL
lsof -ti:6379 | xargs kill -9  # Redis

# If PostgreSQL keeps restarting, it may be a system service
# Docker will handle port conflicts, or you can change the port in docker-compose.yml
```

## Step 1: Start Infrastructure Services (PostgreSQL, Redis)

```bash
cd infra
./docker-compose.sh up -d postgres redis
# Or: docker-compose --env-file ../.env -f docker-compose.yml up -d postgres redis
```

Wait ~10 seconds for services to be healthy. Verify:
```bash
./docker-compose.sh ps
```
Both `postgres` and `redis` should show status "healthy".

## Step 2: Start Theory Engine API (Backend)

**Option A: Run in Docker (Recommended)**
```bash
cd infra
./docker-compose.sh up -d theory-engine-api
# Or: docker-compose --env-file ../.env -f docker-compose.yml up -d theory-engine-api
```

Wait ~15 seconds, then verify:
```bash
curl http://localhost:8000/healthz
```
Should return: `{"status":"ok"}`

**Note:** If you see multiple containers with the same image, clean them up:
```bash
docker ps -a | grep "infra-theory-engine-api" | grep -v "dock108-theory-api" | awk '{print $1}' | xargs docker rm -f
```

**Option B: Run Locally (For Development)**
```bash
cd services/theory-engine-api
uv run uvicorn app.main:app --reload --port 8000
```

## Step 3: Start Celery Worker (For Background Jobs)

```bash
cd infra
./docker-compose.sh up -d worker
# Or: docker-compose --env-file ../.env -f docker-compose.yml up -d worker
```

Or run locally:
```bash
cd services/data-workers
uv run celery -A app.main worker --loglevel=info
```

## Step 4: Start Frontend Apps (As Needed)

**Theory Bets Web (Port 3001):**
```bash
cd apps/theory-bets-web
pnpm dev --port 3001
```

**Other apps:**
- `apps/dock108-web` - Port 3000
- `apps/prompt-game-web` - Port 3002
- `apps/theory-crypto-web` - Port 3005
- `apps/conspiracy-web` - Port 3004
- `apps/highlights-web` - Port 3005
- `apps/playlist-web` - Port 3003

## Quick Start (All Services)

To start everything at once:
```bash
cd infra
./docker-compose.sh up -d
# Or: docker-compose --env-file ../.env -f docker-compose.yml up -d
```

This starts:
- PostgreSQL (5432)
- Redis (6379)
- Theory Engine API (8000)
- Celery Worker
- All web apps (if configured)

## Verify Everything is Running

```bash
# Check Docker services
cd infra
./docker-compose.sh ps

# Check backend health
curl http://localhost:8000/healthz

# Check ports
lsof -i :8000  # Backend
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
```

## Troubleshooting

**Backend not starting?**
- Check logs: `cd infra && ./docker-compose.sh logs theory-engine-api`
- Verify `.env` file exists in repo root with `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `DATABASE_URL`, `REDIS_URL`, etc.
- Make sure PostgreSQL and Redis are healthy first
- Ensure you're using `./docker-compose.sh` or `--env-file ../.env` to load environment variables

**Port already in use?**
- Kill processes: `lsof -ti:PORT | xargs kill -9`
- Or stop Docker: `cd infra && ./docker-compose.sh down`

**Database connection errors?**
- Wait longer for PostgreSQL to be fully ready (~30 seconds)
- Check: `cd infra && ./docker-compose.sh logs postgres`

