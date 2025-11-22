# Highlights API Documentation

## Overview

The Highlights API provides endpoints for planning and retrieving sports highlight playlists. It integrates AI parsing, guardrails, YouTube search, and intelligent caching.

## Endpoints

### POST /api/highlights/plan

Plan a sports highlight playlist from natural language query.

**Request Body**:
```json
{
  "query_text": "NFL Week 12 highlights, 2 hours",
  "mode": "sports_highlight",
  "user_id": "optional-user-id"
}
```

**Response** (201 Created):
```json
{
  "playlist_id": 123,
  "query_id": 45,
  "items": [
    {
      "video_id": "dQw4w9WgXcQ",
      "title": "NFL Week 12 Highlights",
      "description": "...",
      "channel_id": "UC...",
      "channel_title": "NFL",
      "duration_seconds": 600,
      "published_at": "2024-11-18T12:00:00Z",
      "view_count": 1000000,
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "thumbnail_url": "https://...",
      "scores": {
        "highlight_score": 0.9,
        "channel_reputation": 1.0,
        "view_count_normalized": 0.8,
        "freshness_score": 0.95,
        "final_score": 0.91
      },
      "tags": []
    }
  ],
  "total_duration_seconds": 7200,
  "cache_status": "fresh",
  "explanation": {
    "assumptions": ["Interpreted '2 hours' as 120 minutes"],
    "filters_applied": {
      "content_types": ["highlights"],
      "exclusions": [],
      "nsfw_filter": true
    },
    "ranking_factors": {
      "highlight_score_weight": 0.3,
      "channel_reputation_weight": 0.3,
      "view_count_weight": 0.2,
      "freshness_weight": 0.2
    },
    "coverage_notes": [],
    "total_candidates": 50,
    "selected_videos": 12,
    "actual_duration_minutes": 120.0,
    "target_duration_minutes": 120
  },
  "created_at": "2024-11-18T12:00:00Z",
  "stale_after": "2024-11-18T18:00:00Z",
  "disclaimer": "This app builds playlists using public YouTube videos. We do not host or control the content."
}
```

**Process Flow**:
1. Normalize and check guardrails
2. Parse query with AI → structured spec
3. Compute normalized signature
4. Check DB for existing non-stale playlist
5. If found: return cached playlist
6. If not: search YouTube, build playlist, save to DB, return fresh

**Error Responses**:
- `400 Bad Request`: Guardrail violation
- `500 Internal Server Error`: Parsing or search failure

### GET /api/highlights/{playlist_id}

Retrieve detailed playlist information.

**Response** (200 OK):
```json
{
  "playlist_id": 123,
  "query_id": 45,
  "query_text": "NFL Week 12 highlights, 2 hours",
  "items": [...],
  "total_duration_seconds": 7200,
  "explanation": {
    "assumptions": [...],
    "filters_applied": {...},
    "ranking_factors": {...},
    "coverage_notes": [...]
  },
  "created_at": "2024-11-18T12:00:00Z",
  "stale_after": "2024-11-18T18:00:00Z",
  "query_metadata": {
    "mode": "sports_highlight",
    "requested_duration_minutes": 120,
    "version": 1,
    "created_at": "2024-11-18T12:00:00Z",
    "last_used_at": "2024-11-18T12:00:00Z"
  }
}
```

**Error Responses**:
- `404 Not Found`: Playlist not found

### POST /api/highlights/{playlist_id}/watch-token

Generate a temporary watch token for a playlist. The token expires after 48 hours and can be used to access the playlist via the `/api/highlights/watch/{token}` endpoint.

**Response** (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "watch_url": "/watch/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-11-20T12:00:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Playlist not found

### GET /api/highlights/watch/{token}

Get playlist data using a watch token. This endpoint validates the token and returns playlist data if valid.

**Response** (200 OK):
Same structure as `GET /api/highlights/{playlist_id}`

**Error Responses**:
- `403 Forbidden`: Token is invalid or expired

**Note**: Tokens expire after 48 hours. Generate a new token from the playlist page if expired.

### GET /api/highlights/metrics

Get metrics for highlight playlists (sports requested, average duration, cache hit rate).

**Query Parameters**:
- `days` (optional, default: 30) - Number of days to look back

**Response** (200 OK):
```json
{
  "period_days": 30,
  "sports_request_counts": {
    "NFL": 45,
    "NBA": 32,
    "MLB": 28
  },
  "average_playlist_duration_minutes": 87.5,
  "cache_statistics": {
    "hit_rate": 62.3,
    "total_requests": 150,
    "cache_hits": 93,
    "cache_misses": 57,
    "period_days": 30
  }
}
```

### GET /api/highlights/metrics/csv

Get metrics as CSV for simple dashboard.

**Query Parameters**:
- `days` (optional, default: 30) - Number of days to look back

**Response** (200 OK):
```
Metric,Value
Average Playlist Duration (minutes),87.5
Cache Hit Rate (%),62.3
Total Requests,150
Cache Hits,93
Cache Misses,57

Sport,Request Count
NFL,45
NBA,32
MLB,28
```

## Explanation Structure

Each playlist includes an `explanation` JSON object with:

### assumptions
List of assumptions made during parsing:
- `"Interpreted 'full work day' as 8 hours (480 minutes)"`
- `"Assumed NFL for ambiguous sport reference"`

### filters_applied
Filters used during search and selection:
```json
{
  "content_types": ["highlights", "bloopers"],
  "exclusions": ["no Jets"],
  "nsfw_filter": true
}
```

### ranking_factors
Scoring weights used for ranking:
```json
{
  "highlight_score_weight": 0.3,
  "channel_reputation_weight": 0.3,
  "view_count_weight": 0.2,
  "freshness_weight": 0.2
}
```

### coverage_notes
Notes about coverage gaps or substitutions:
- `"Only found 90 minutes of content (target: 120 minutes). Consider expanding search criteria."`
- `"No highlights found for XYZ, substituted with top plays for league instead"`

### Statistics
```json
{
  "total_candidates": 50,
  "selected_videos": 12,
  "actual_duration_minutes": 120.0,
  "target_duration_minutes": 120
}
```

## Caching

Playlists are cached based on normalized signatures:

- **Same signature + not stale** → Return cached playlist (`cache_status: "cached"`)
- **Same signature + stale** → Rebuild playlist (`cache_status: "fresh"`)
- **New signature** → Build new playlist (`cache_status: "fresh"`)

Staleness is computed based on event recency:
- Events < 2 days old: 6 hours
- Events 2-30 days old: 3 days
- Events >30 days old: Never expires

## Example Usage

### Python

```python
import httpx

# Plan playlist
response = httpx.post(
    "http://localhost:8000/api/highlights/plan",
    json={
        "query_text": "NFL Week 12 highlights, 2 hours",
        "mode": "sports_highlight"
    }
)
playlist = response.json()

# Get playlist details
playlist_id = playlist["playlist_id"]
detail_response = httpx.get(f"http://localhost:8000/api/highlights/{playlist_id}")
detail = detail_response.json()
```

### cURL

```bash
# Plan playlist
curl -X POST http://localhost:8000/api/highlights/plan \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "NFL Week 12 highlights, 2 hours",
    "mode": "sports_highlight"
  }'

# Get playlist
curl http://localhost:8000/api/highlights/123
```

## Integration Notes

- **Guardrails**: Checked before parsing (hard blocks reject immediately)
- **AI Parsing**: Uses OpenAI to convert natural language to structured spec
- **YouTube Search**: Uses `sports_search.py` for sports-focused search
- **Scoring**: Multi-factor scoring (highlight keywords, channel reputation, views, freshness)
- **Database**: Stores queries and playlists with normalized signatures for caching

