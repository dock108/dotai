# Infrastructure

This directory contains deployment configuration for Hetzner.

## Structure

- `docker-compose.yml` - Main orchestration file for all services
- `docker/` - Dockerfiles for each service
- `nginx/` - Nginx reverse proxy configuration
- `DEPLOYMENT.md` - Deployment guide

## Services

### Core Services
- **nginx** - Reverse proxy and SSL termination
- **postgres** - PostgreSQL database
- **redis** - Redis cache
- **theory-engine-api** - FastAPI backend
- **worker** - Celery workers for async jobs

### Frontend Apps
- **dock108-web** - Main landing page
- **game-web** - AI prompting game
- **playlist-web** - Playlist curator
- **theory-bets-web** - Bets theory surface
- **theory-crypto-web** - Crypto theory surface
- **theory-stocks-web** - Stocks theory surface
- **theory-conspiracy-web** - Conspiracies theory surface

## Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

See `DEPLOYMENT.md` for full deployment instructions.

