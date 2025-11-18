# Deployment Guide - Hetzner

This guide covers deploying dock108 to Hetzner bare metal or cloud instances.

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
   docker-compose up -d
   ```

5. **Run database migrations**:
   ```bash
   docker-compose exec theory-engine-api alembic upgrade head
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

### Option 1: Let's Encrypt with Certbot

1. Install certbot:
   ```bash
   apt-get update && apt-get install -y certbot
   ```

2. Generate certificates:
   ```bash
   certbot certonly --standalone -d dock108.ai -d *.dock108.ai
   ```

3. Update nginx config to use SSL (see `nginx/conf.d/dock108.conf`)

### Option 2: Traefik (Alternative)

Replace nginx with Traefik for automatic SSL:

```yaml
traefik:
  image: traefik:v2.10
  command:
    - "--api.insecure=true"
    - "--providers.docker=true"
    - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
    - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./letsencrypt:/letsencrypt
```

## Subdomain Routing

The nginx configuration routes subdomains as follows:

- `dock108.ai` → `dock108-web` (main landing)
- `game.dock108.ai` → `game-web`
- `playlist.dock108.ai` → `playlist-web`
- `bets.dock108.ai` → `theory-bets-web`
- `crypto.dock108.ai` → `theory-crypto-web`
- `stocks.dock108.ai` → `theory-stocks-web`
- `conspiracies.dock108.ai` → `theory-conspiracy-web`
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
   - Node 1: Frontend apps (nginx + Next.js apps)
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

### Nginx routing issues

1. Check nginx config: `docker-compose exec nginx nginx -t`
2. View access logs: `docker-compose logs nginx`
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

