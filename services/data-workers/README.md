# Data Workers

Async tasks + cron jobs that fetch/cache external data (YouTube, odds, prices, news) for the theory engine.

## Structure
```
data-workers/
  pyproject.toml
  app/
    __init__.py
    main.py          # Celery app configuration
    config.py        # Settings management
    workers/
      __init__.py
      youtube_cache.py    # Pre-fetch popular sports queries
      odds_snapshot.py    # Cache betting odds data
      market_prices.py    # Cache crypto/stock prices
```

## Responsibilities
- Normalize third-party API responses
- Store results in Redis with TTLs + lineage metadata
- Pre-fetch popular queries to reduce API latency
- Push alerts to the theory engine when significant data changes occur

## Running Locally

1. Install dependencies:
   ```bash
   cd services/data-workers
   uv sync
   ```

2. Start Redis (if not already running):
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. Set environment variables:
   ```bash
   export REDIS_URL=redis://localhost:6379/0
   export CELERY_BROKER_URL=redis://localhost:6379/0
   export CELERY_RESULT_BACKEND=redis://localhost:6379/0
   export YOUTUBE_API_KEY=your_key_here
   ```

4. Start Celery worker:
   ```bash
   uv run celery -A app.main worker --loglevel=info
   ```

5. Start Celery beat (for scheduled tasks):
   ```bash
   uv run celery -A app.main beat --loglevel=info
   ```

## Workers

### YouTube Cache Worker
- Pre-fetches popular sports queries
- Caches results in Redis with 1-hour TTL
- Reduces API latency for common queries

### Odds Snapshot Worker
- Fetches betting odds data (placeholder)
- Caches in Redis with 5-minute TTL
- Scheduled daily for major sports

### Market Prices Worker
- Fetches crypto and stock prices (placeholder)
- Crypto: 1-minute TTL
- Stocks: 5-minute TTL
- Scheduled intraday during market hours

## Docker

The worker service is configured in `infra/docker-compose.yml` and uses the `infra/docker/worker.Dockerfile`.

Use the same `py-core` schemas to ensure API ↔ worker parity.
