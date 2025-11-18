# Py Core

Python package that stores shared schemas, guardrail helpers, scoring utilities, and client wrappers.

## Modules

### Schemas
- `schemas/theory.py` – TheorySubmission, TheoryCard, GuardrailVerdict
- `schemas/highlight_request.py` – HighlightRequestSpec, Sport, LoopMode, ContentMix, DateRange

### Guardrails
- `guardrails/engine.py` – General guardrail evaluation
- `guardrails/sports_highlights.py` – Sports-specific guardrails

### Scoring
- `scoring/metrics.py` – Domain-specific verdict computation
- `scoring/video.py` – Video scoring utilities for playlist generation

### Clients
- `clients/youtube.py` – YouTube Data API client wrapper with authentication support

### Data
- `data/cache.py` – Context caching with domain-specific TTL rules
- `data/fetchers.py` – Data fetch interfaces for each theory domain

### Playlist
- `playlist/staleness.py` – Staleness computation for playlist caching based on event recency

## Usage

```python
from py_core import (
    YouTubeClient,
    VideoCandidate,
    calculate_highlight_score,
    compute_stale_after,
    should_refresh_playlist,
)

# Use YouTube client
client = YouTubeClient(api_key="...")
videos = await client.search("NFL highlights")

# Score videos
scores = calculate_highlight_score(video, event_date, "NFL")

# Compute staleness
stale_after = compute_stale_after(event_date, now, "sports_highlight")
```

First consumer is `services/theory-engine-api`, followed by `services/data-workers` and the original "algorithm buster" playlist builder.
