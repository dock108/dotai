# Theory Bets Scraper

Config-driven ingestion service that fetches historical boxscores and closing odds for the Sports Betting Theory Engine.

## Features

- Per-sport scraper modules (NBA, NCAAB, etc.) that normalize data into the shared Postgres schema.
- Celery-based job runner so admin users can trigger scrapes, backfills, or one-off rescrapes.
- Odds API integration for mainline markets (spread, total, moneyline) with book filtering.
- Idempotent persistence helpers that upsert games, team boxscores, player boxscores, and odds.

## Layout

```
app/
  config.py            # Pydantic settings
  logging.py           # Structlog configuration
  celery_app.py        # Celery app, queue registration
  db.py                # SQLAlchemy session helpers
  models/              # Typed payloads shared across scrapers
  persistence.py       # Upsert helpers + scrape versioning logic
  scrapers/
    base.py            # Abstract base class for sport scrapers
    nba_sportsref.py   # Basketball Reference scraper (NBA)
    ncaab_sportsref.py # College basketball scraper
  odds/
    client.py          # Odds API client
    synchronizer.py    # Upsert logic for odds snapshots
  jobs/
    tasks.py           # Celery tasks triggered by admin UI
  services/
    run_manager.py     # High-level orchestration per scrape run
```

## Local development

1. Install dependencies (at repo root):

```bash
cd services/theory-bets-scraper
uv sync
```

2. Export environment variables (see `app/config.py` for the full list):

```
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dock108
ODDS_API_KEY=...
REDIS_URL=redis://localhost:6379/1
```

3. Start Celery worker:

```bash
uv run celery -A app.celery_app.app worker --loglevel=info
```

4. Trigger a scrape run via FastAPI admin endpoint or CLI helper (coming soon).

## Notes

- The scraper relies on the shared models defined in `services/theory-engine-api/app/db_models.py`.
- Scrape runs should always be initiated via the API so `sports_scrape_runs` rows stay authoritative.
- This directory ships reusable utilities; individual sport scrapers can be iterated without touching the admin UI.

