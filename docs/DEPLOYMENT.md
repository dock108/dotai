# Production Deployment Guide - Full Monorepo

## Scope

**This guide covers production deployment for the entire dock108 monorepo:**
- All frontend apps (`dock108-web`, `prompt-game-web`, `playlist-web`, `highlights-web`, `theory-*-web`)
- Backend services (`theory-engine-api`, `data-workers`)
- Infrastructure (PostgreSQL, Redis, Traefik reverse proxy)

**For local development of individual features (e.g., Sports Highlight Channel), see `docs/LOCAL_DEPLOY.md`.**

## Overview

This guide covers deploying the full dock108 monorepo to Hetzner bare metal or cloud instances.

## Prerequisites

- Hetzner server (recommended: CX31 or larger for production)
- Docker and Docker Compose installed
- Domain name configured with DNS pointing to Hetzner server IP
- SSL certificates (Let's Encrypt recommended)

## Quick Start

1. **Clone repository**:
   ```bash
   git clone <repo-url> /opt/dock108
   cd /opt/dock108
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your secrets
   ```

3. **Configure DNS**:
   - Point `dock108.ai` → server IP
   - Point `*.dock108.ai` → server IP (wildcard for subdomains)

4. **Start services**:
   ```bash
   cd infra
   ./docker-compose.sh up -d
   # Or: docker-compose --env-file ../.env -f docker-compose.yml up -d
   ```

5. **Run database migrations**:
   ```bash
   ./docker-compose.sh exec theory-engine-api alembic upgrade head
   # Or: docker-compose --env-file ../.env -f docker-compose.yml exec theory-engine-api alembic upgrade head
   ```

## Environment Variables

Create a `.env` file in the project root:

```bash
# Database
POSTGRES_DB=dock108
POSTGRES_USER=dock108
POSTGRES_PASSWORD=<strong-password>

# Redis
REDIS_PASSWORD=<strong-password>

# API Keys
OPENAI_API_KEY=<your-key>
YOUTUBE_API_KEY=<your-key>

# Environment
ENVIRONMENT=production
```

## SSL/TLS Setup

Traefik ships in `docker-compose.yml` with an ACME (Let's Encrypt) resolver enabled. To activate:

1. Set `LETSENCRYPT_EMAIL` in your root `.env`.
2. Ensure `infra/traefik/acme` exists and is writable by Docker (Traefik stores certificates in `acme/acme.json`).
3. Start the stack (`docker-compose up -d traefik ...`). Traefik will automatically request certificates for every router label that specifies `tls.certresolver=letsencrypt`.

No separate certbot step is required. If you ever need to import custom certificates, mount them into the Traefik container and reference them via a TLS store entry.

## Subdomain Routing

Traefik routes subdomains via the labels defined in `docker-compose.yml`:

- `dock108.ai` → `dock108-web` (main landing)
- `game.dock108.ai` → `prompt-game-web`
- `playlist.dock108.ai` → `playlist-web`
- `bets.dock108.ai` → `theory-bets-web`
- `crypto.dock108.ai` → `theory-crypto-web`
- `stocks.dock108.ai` → `theory-stocks-web`
- `conspiracies.dock108.ai` → `conspiracy-web`
- `api.dock108.ai` → `theory-engine-api`

## Database Migrations

Run migrations on first deploy and after code updates:

```bash
docker-compose exec theory-engine-api alembic upgrade head
```

## Monitoring

### Health Checks

All services include health checks. Monitor with:

```bash
docker-compose ps
```

### Logs

View logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f theory-engine-api
```

### Database Backup

Backup PostgreSQL:

```bash
docker-compose exec postgres pg_dump -U dock108 dock108 > backup.sql
```

Restore:

```bash
docker-compose exec -T postgres psql -U dock108 dock108 < backup.sql
```

## Scaling

### Single Node (Current Setup)

All services run on one server. Suitable for:
- Development
- Staging
- Small production (< 1000 requests/day)

### Multi-Node (Future)

For larger scale, migrate to Kubernetes:

1. Split services across nodes:
   - Node 1: Frontend apps (Traefik + Next.js apps)
   - Node 2: Backend (API + workers)
   - Node 3: Database + Redis (or use managed services)

2. Use Hetzner Cloud Load Balancer for high availability

## Maintenance

### Update Services

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

### Database Maintenance

```bash
# Connect to database
docker-compose exec postgres psql -U dock108 dock108

# Vacuum database
docker-compose exec postgres psql -U dock108 dock108 -c "VACUUM ANALYZE;"
```

## Troubleshooting

### Services won't start

1. Check logs: `docker-compose logs`
2. Verify environment variables: `docker-compose config`
3. Check port conflicts: `netstat -tulpn | grep :80`

### Database connection errors

1. Verify PostgreSQL is healthy: `docker-compose ps postgres`
2. Check connection string in `.env`
3. Verify network: `docker network inspect dock108_dock108-network`

### Traefik routing issues

1. Check router status: `docker-compose logs traefik`
2. Inspect dynamic config: `docker-compose exec traefik traefik healthcheck`
3. Verify DNS resolution: `dig dock108.ai`

## Security

- Change all default passwords in `.env`
- Use strong passwords for PostgreSQL and Redis
- Enable firewall (UFW recommended):
  ```bash
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw enable
  ```
- Keep Docker and system packages updated
- Use SSL/TLS for all traffic (redirect HTTP → HTTPS)

