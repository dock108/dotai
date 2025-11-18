# Data Workers

Async tasks + cron jobs that fetch/cache external data (YouTube, odds, prices, news) for the theory engine.

## Proposed layout
```
data-workers/
  pyproject.toml
  workers/
    youtube_cache.py
    odds_snapshot.py
    market_prices.py
    news_digest.py
  shared/
    clients/
    storage/
```

## Responsibilities
- Normalize third-party API responses
- Store results in Redis/Postgres with TTLs + lineage metadata
- Push alerts to the theory engine when significant data changes occur

Use the same `py-core` schemas to ensure API ↔ worker parity.
