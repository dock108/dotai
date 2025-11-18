# Playlist Database Schema

## Overview

The playlist database schema supports both sports highlight playlists and general playlists with intelligent caching based on event recency.

## Tables

### `playlist_queries`

Stores normalized playlist queries for caching and deduplication.

**Fields**:
- `id` (BigInteger, PK) - Unique query ID
- `query_text` (Text) - Raw user input
- `normalized_signature` (String(64), indexed) - Hash of structured spec (sport, leagues, teams, date_range, etc.)
- `mode` (String(30), indexed) - `sports_highlight` or `general_playlist`
- `requested_duration_minutes` (Integer) - Target playlist duration
- `created_at` (DateTime) - When query was first created
- `last_used_at` (DateTime) - Last time query was used (auto-updated)
- `version` (Integer) - Schema version for scoring/parsing changes

**Indexes**:
- `idx_queries_signature_mode` - Composite index on (normalized_signature, mode)
- `idx_queries_created` - Index on created_at

**Purpose**: 
- Deduplicate equivalent queries
- Track query usage for analytics
- Support schema versioning for parsing/scoring changes

### `playlists`

Stores generated playlists with video items.

**Fields**:
- `id` (BigInteger, PK) - Unique playlist ID
- `query_id` (BigInteger, FK → playlist_queries.id) - Associated query
- `items` (JSONB) - List of video objects with structure:
  ```json
  {
    "video_id": "dQw4w9WgXcQ",
    "title": "Video Title",
    "channel_id": "UC...",
    "duration": 180,
    "source_score": 0.85,
    "freshness_score": 0.92,
    "tag": "intro|context|deep_dive|ending|misc"
  }
  ```
- `total_duration_seconds` (Integer) - Total playlist duration
- `created_at` (DateTime) - When playlist was generated
- `stale_after` (DateTime, nullable, indexed) - When playlist becomes stale (computed based on event recency)

**Indexes**:
- `idx_playlists_stale_after` - Index on stale_after for efficient stale query lookups
- `idx_playlists_query_created` - Composite index on (query_id, created_at)

**Purpose**:
- Cache generated playlists
- Support staleness-based refresh logic
- Store flexible video metadata in JSONB

### `videos` (Optional)

Cached video metadata for deduplication and analytics.

**Fields**:
- `video_id` (String(20), PK) - YouTube video ID
- `title` (Text) - Video title
- `channel_id` (String(50), indexed) - YouTube channel ID
- `duration_seconds` (Integer) - Video duration
- `published_at` (DateTime, indexed) - Publication date
- `tags` (JSONB) - Video tags
- `is_sports_highlight` (Boolean, nullable, indexed) - Whether video is a sports highlight (or score 0-1)
- `last_refreshed_at` (DateTime) - Last time metadata was refreshed

**Indexes**:
- `idx_videos_channel_published` - Composite index on (channel_id, published_at)
- `idx_videos_sports_highlight` - Index on is_sports_highlight

**Purpose**:
- Avoid repeated YouTube API calls for same videos
- Support analytics queries
- Enable video deduplication across playlists

## Staleness Logic

Playlists have intelligent staleness based on event recency:

### Rules

1. **Events < 2 days old**: `stale_after = created_at + 6 hours`
   - Recent events need frequent updates as new highlights are posted

2. **Events 2-30 days old**: `stale_after = created_at + 3 days`
   - Moderately recent events have less frequent updates

3. **Events >30 days old**: `stale_after = None` (never expires)
   - Old events rarely change, so playlists are cached indefinitely
   - Can be manually refreshed or refreshed on schema version changes

### Implementation

See `app/playlist_staleness.py`:
- `compute_stale_after(event_date, now, mode)` - Compute staleness timestamp
- `is_stale(stale_after, now)` - Check if playlist is stale
- `should_refresh_playlist(...)` - Determine if refresh is needed

### Usage Example

```python
from app.playlist_staleness import compute_stale_after, should_refresh_playlist
from app.db_models import PlaylistMode
from datetime import datetime, timedelta

# Event from 1 day ago
event_date = datetime.utcnow() - timedelta(days=1)
now = datetime.utcnow()

# Compute staleness (6 hours for <2 day old events)
stale_after = compute_stale_after(event_date, now, PlaylistMode.sports_highlight)
# stale_after = now + timedelta(hours=6)

# Check if refresh needed
should_refresh = should_refresh_playlist(
    playlist_created_at=now - timedelta(hours=7),
    stale_after=stale_after,
    now=now,
    force_refresh=False,
    schema_version_changed=False
)
# should_refresh = True (playlist is stale)
```

## Query Normalization

Queries are normalized using structured specifications to enable caching:

### PlaylistQuerySpec

```python
@dataclass
class PlaylistQuerySpec:
    sport: str | None
    leagues: list[str] | None
    teams: list[str] | None
    date_range: dict[str, Any] | None
    mix: list[str] | None  # ["highlights", "bloopers", "upsets"]
    duration_bucket: str | None
    exclusions: list[str] | None
    language: str = "en"
    mode: PlaylistMode
```

### Signature Generation

The `normalized_signature` is a SHA-256 hash of the normalized spec:

```python
from app.playlist_helpers import generate_normalized_signature, PlaylistQuerySpec

spec = PlaylistQuerySpec(
    sport="NFL",
    leagues=["NFL"],
    date_range={"start": "2024-11-01", "end": "2024-11-18"},
    mix=["highlights"],
    duration_bucket="60_180",
    mode=PlaylistMode.sports_highlight
)

signature = generate_normalized_signature(spec)
# Returns: "a1b2c3d4..." (64 char hex string)
```

Two queries with the same normalized signature will:
- Share the same cached playlist (if not stale)
- Be deduplicated in the database

## Migration

Run migrations to create tables:

```bash
cd services/theory-engine-api
alembic upgrade head
```

Migration file: `alembic/versions/002_add_playlist_tables.py`

## Future Enhancements

1. **LLM-based query parsing**: Implement `parse_query_to_spec()` to extract structured data from natural language
2. **Video deduplication**: Use `videos` table to avoid duplicate video lookups
3. **Analytics**: Query `playlist_queries` and `playlists` for usage analytics
4. **Schema versioning**: Use `version` field to invalidate old playlists when parsing/scoring logic changes

