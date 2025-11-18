# Theory Engine API

FastAPI service that powers every dock108 surface.

## Status

✅ **Phase 2 Complete**: Basic API skeleton with `/api/theory/evaluate` endpoint  
✅ **Phase 3 Complete**: Database models (SQLAlchemy) and caching layer

## Database Setup

The service uses PostgreSQL with SQLAlchemy async. Models are defined in `app/db_models.py`:

- `customer_accounts` - User tiers (free/silver/gold/unlimited)
- `theories` - Stored theory submissions
- `evaluations` - Evaluation results linked to theories
- `external_context_cache` - Cached API responses (YouTube, odds, prices, etc.)

### Initial Setup

1. Create database:
   ```bash
   createdb dock108
   ```

2. Run migrations:
   ```bash
   alembic upgrade head
   ```

3. Or initialize tables directly (dev only):
   ```python
   from app.db import init_db
   await init_db()
   ```

## Caching

The `ContextCache` helper (`py_core.data.cache`) implements domain-specific TTL rules:

- **YouTube**: 7-day cache with similarity matching
- **Sports (odds/play-by-play)**: Time-based TTL (events >30 days old never expire)
- **Crypto/Stocks**: 5-15 minute intraday cache

Cache entries are stored in `external_context_cache` table with `key_hash` (SHA-256 of query params).

## API Endpoints

- `GET /healthz` - Health check
- `POST /api/theory/evaluate` - Evaluate a theory submission

See `docs/THEORY_ENGINE.md` for the full blueprint.
