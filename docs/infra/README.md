# Infrastructure

This directory contains deployment configuration for Hetzner.

## Structure

- `docker-compose.yml` - Main orchestration file for all services
- `docker/` - Dockerfiles for each service
- `traefik/` - Traefik config + ACME storage for TLS
- `docs/DEPLOYMENT.md` - Deployment guide (moved to docs/)

## Services

### Core Services
- **traefik** - Reverse proxy and Let's Encrypt automation
- **postgres** - PostgreSQL database
- **redis** - Redis cache
- **theory-engine-api** - FastAPI backend
- **worker** - Celery workers for async jobs

### Frontend Apps
- **dock108-web** - Main landing page / portal
- **prompt-game-web** - AI prompting game
- **playlist-web** - Playlist curator
- **highlights-web** - Sports highlights utility
- **theory-bets-web** - Bets theory surface
- **theory-crypto-web** - Crypto theory surface
- **theory-stocks-web** - Stocks theory surface
- **conspiracy-web** - Conspiracy decoder surface

## Quick Start

The `.env` file is located in the repo root. Use the wrapper script to automatically load it:

```bash
# Start all services
./docker-compose.sh up -d

# View logs
./docker-compose.sh logs -f

# Stop all services
./docker-compose.sh down
```

Or use docker-compose directly with the env file:

```bash
# From infra/ directory
docker-compose --env-file ../.env -f docker-compose.yml up -d

# Or from repo root
docker-compose --env-file .env -f infra/docker-compose.yml up -d
```

**Important**: The `.env` file in the repo root is the single source of truth. All passwords and configuration must be set there. Never hardcode passwords in docker-compose.yml.

See [`DEPLOYMENT.md`](../DEPLOYMENT.md) for full deployment instructions.

