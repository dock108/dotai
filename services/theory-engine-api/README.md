# Theory Engine API

FastAPI service that powers every dock108 surface.

## Status

✅ **Phase 2 Complete**: Basic API skeleton with `/api/theory/evaluate` endpoint  
✅ **Phase 3 Complete**: Database models (SQLAlchemy) and caching layer  
✅ **Phase 4 Complete**: Sports highlight playlist generation with AI parsing, guardrails, and intelligent caching

## Database Setup

The service uses PostgreSQL with SQLAlchemy async. Models are defined in `app/db_models.py`:

- `customer_accounts` - User tiers (free/silver/gold/unlimited)
- `theories` - Stored theory submissions
- `evaluations` - Evaluation results linked to theories
- `external_context_cache` - Cached API responses (YouTube, odds, prices, etc.)
- `playlist_queries` - Normalized playlist queries with metadata (sport, league, teams, event_date, is_playoff)
- `playlists` - Generated playlists with video items and staleness tracking
- `videos` - Cached video metadata for deduplication

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

### Theory Evaluation
- `GET /healthz` - Health check
- `POST /api/theory/evaluate` - Evaluate a theory submission

### Sports Highlights
- `POST /api/highlights/plan` - Plan a highlight playlist from user query
- `GET /api/highlights/{playlist_id}` - Get detailed playlist information
- `POST /api/highlights/{playlist_id}/watch-token` - Generate a temporary watch token (48-hour expiration)
- `GET /api/highlights/watch/{token}` - Get playlist data using a watch token
- `GET /api/highlights/metrics` - Get metrics (sports requested, avg duration, cache hit rate)
- `GET /api/highlights/metrics/csv` - Get metrics as CSV for dashboard

### Other Domains
- `POST /api/bets/evaluate` - Evaluate betting theory
- `POST /api/crypto/evaluate` - Evaluate crypto theory
- `POST /api/stocks/evaluate` - Evaluate stock theory
- `POST /api/conspiracies/evaluate` - Evaluate conspiracy theory
- `POST /api/playlist/evaluate` - Evaluate playlist request

See `docs/THEORY_ENGINE.md` for the full blueprint and `docs/HIGHLIGHTS_API.md` for highlights API documentation.
