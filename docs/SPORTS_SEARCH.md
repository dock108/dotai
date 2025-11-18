# Sports-Focused YouTube Search

## Overview

The `sports_search.py` module provides sports-focused YouTube search functionality with intelligent query generation, channel reputation scoring, and highlight detection.

## Features

- **Structured search specifications** - Define searches using sport, league, teams, dates, content types
- **Intelligent query generation** - Automatically builds multiple search queries from spec
- **Channel reputation scoring** - Prioritizes official league/team channels
- **Highlight detection** - Identifies highlight videos via keyword matching
- **Multi-factor scoring** - Combines highlight keywords, channel reputation, view count, and freshness

## Usage

### Basic Example

```python
from app.sports_search import SportsSearchSpec, search_youtube_sports

# Search for NFL Week 12 highlights
spec = SportsSearchSpec(
    sport="NFL",
    league="NFL",
    date_range={"start": "2024-11-17", "end": "2024-11-24"},
    content_types=["highlights", "top plays"],
    duration_target_minutes=10,
)

candidates = await search_youtube_sports(spec, max_results=20)
```

### SportsSearchSpec

```python
@dataclass
class SportsSearchSpec:
    sport: str  # NFL, NBA, MLB, NHL, NCAAF, NCAAB, PGA, F1, etc.
    league: str | None = None
    teams: list[str] | None = None
    date_range: dict[str, Any] | None = None  # {"start": "2024-11-01", "end": "2024-11-18"} or {"date": "2024-11-12"}
    content_types: list[str] | None = None  # ["highlights", "bloopers", "top plays", "full game", "condensed"]
    duration_target_minutes: int = 10
```

### Query Generation

The `build_search_queries()` function generates multiple search queries based on available information:

**Team vs Team**:
- `"{team1} vs {team2} highlights {date}"`
- `"{team1} vs {team2} bloopers {date}"`

**League-level**:
- `"{league} highlights {date}"`
- `"{league} top plays {year}"`

**Sport-level** (fallback):
- `"{sport} highlights {date}"`
- `"{sport} bloopers {year}"`

### Scoring System

Videos are scored using multiple factors:

#### 1. Highlight Score (30% weight)
- Detects keywords: "highlight", "highlights", "condensed", "recap", "top plays", "bloopers", etc.
- Normalized to 0-1 based on keyword matches

#### 2. Channel Reputation (30% weight)
- **Official channels**: 1.0 (NFL, NBA, MLB official channels)
- **Major networks**: 0.8 (ESPN, Fox Sports, CBS Sports)
- **Others**: 0.5

#### 3. View Count Normalized (20% weight)
- Log-scale normalization
- Typical highlights: 10K-10M views
- Formula: `min((log10(views) - 3) / 4.0, 1.0)`

#### 4. Freshness Score (20% weight)
- Based on difference between video publish date and event date
- Same day: 1.0
- 1 day: 0.9
- 3 days: 0.7
- 7 days: 0.5
- 30 days: 0.3
- >30 days: 0.1

#### Final Score
```
final_score = (
    highlight_score * 0.3 +
    channel_reputation * 0.3 +
    view_count_normalized * 0.2 +
    freshness_score * 0.2
)
```

### Duration Filters

Content types have associated duration ranges:

- **Top plays / Bloopers**: < 5 minutes (0-300 seconds)
- **Highlights / Condensed**: 5-15 minutes (300-900 seconds)
- **Full game**: > 1 hour (3600+ seconds)
- **Default**: 1-30 minutes (60-1800 seconds)

### Channel Whitelists

Official channels are prioritized in search results:

```python
OFFICIAL_CHANNELS = {
    "NFL": ["UCDVYQ4Zhbm3S2dlz7P1GBDg", ...],
    "NBA": ["UCWJ2lWNubArHWmf3F7bf1zw", ...],
    # ... more leagues
}
```

## Examples

### NFL Week Highlights

```python
spec = SportsSearchSpec(
    sport="NFL",
    league="NFL",
    date_range={"start": "2024-11-17", "end": "2024-11-24"},
    content_types=["highlights"],
    duration_target_minutes=10,
)
```

### MLB Bloopers

```python
spec = SportsSearchSpec(
    sport="MLB",
    league="MLB",
    content_types=["bloopers"],
    duration_target_minutes=5,
)
```

### Team Matchup

```python
spec = SportsSearchSpec(
    sport="NFL",
    teams=["Kansas City Chiefs", "Buffalo Bills"],
    date_range={"date": "2024-11-17"},
    content_types=["highlights", "condensed"],
    duration_target_minutes=15,
)
```

### Multi-Content Type

```python
spec = SportsSearchSpec(
    sport="NFL",
    date_range={"start": "2024-11-17", "end": "2024-11-24"},
    content_types=["highlights", "bloopers", "top plays"],
    duration_target_minutes=10,
)
```

## Integration

The sports search module integrates with:

1. **Playlist generation** - Use search results to build playlists
2. **Caching layer** - Cache search results using `playlist_queries` table
3. **Staleness logic** - Use `compute_stale_after()` for cache invalidation
4. **Video metadata** - Store results in `videos` table for deduplication

## Future Enhancements

1. **Expand channel whitelists** - Add more official channels and networks
2. **Team name normalization** - Handle variations (e.g., "KC Chiefs" vs "Kansas City Chiefs")
3. **Date parsing** - Better handling of relative dates ("Week 12", "last Sunday")
4. **Content type detection** - ML-based detection beyond keyword matching
5. **Regional preferences** - Support for international leagues and channels

