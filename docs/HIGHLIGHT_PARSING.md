# Sports Highlight Request Parsing

## Overview

The AI parsing layer converts natural language user requests into structured `HighlightRequestSpec` objects that can be used to search YouTube and generate playlists.

## Schema

### HighlightRequestSpec

```python
{
  "sport": "NFL|NBA|MLB|NHL|NCAAF|NCAAB|PGA|F1|SOCCER|TENNIS|OTHER",
  "leagues": ["NFL", "AFC"],
  "teams": ["Kansas City Chiefs", "Buffalo Bills"],
  "date_range": {
    "start_date": "2024-11-17",
    "end_date": "2024-11-24",
    "single_date": null,
    "week": "Week 12",
    "season": "2024"
  },
  "content_mix": {
    "highlights": 0.6,
    "bloopers": 0.2,
    "top_plays": 0.2,
    "condensed": 0.0,
    "full_game": 0.0,
    "upsets": 0.0
  },
  "requested_duration_minutes": 120,
  "loop_mode": "single_playlist|loop_1h|loop_full_day",
  "exclusions": ["no Jets", "no Super Bowl replays"],
  "nsfw_filter": true,
  "language": "en",
  "assumptions": [
    "Assumed NFL for ambiguous sport reference",
    "Interpreted 'full work day' as 8 hours (480 minutes)"
  ]
}
```

## Usage

### Basic Parsing

```python
from app.highlight_parser import parse_highlight_request

user_text = "NFL Week 12 highlights, 2 hours"
result = await parse_highlight_request(user_text)

print(result.spec.sport)  # Sport.NFL
print(result.spec.requested_duration_minutes)  # 120
print(result.confidence)  # 0.9
print(result.needs_clarification)  # False
```

### With Guardrails

```python
from py_core.guardrails.sports_highlights import (
    check_sports_highlight_guardrails,
    has_hard_block_sports,
    normalize_sports_request,
)

# Normalize input
normalized = normalize_sports_request(user_text)

# Check guardrails
guardrail_results = check_sports_highlight_guardrails(normalized)

# Block if hard block found
if has_hard_block_sports(guardrail_results):
    raise ValueError("Request blocked by guardrails")

# Parse if passed guardrails
result = await parse_highlight_request(normalized)
```

## Parsing Examples

### Example 1: Simple Request

**Input**: "NFL Week 12 highlights, 2 hours"

**Output**:
```python
HighlightRequestSpec(
    sport=Sport.NFL,
    leagues=["NFL"],
    teams=[],
    date_range=DateRange(week="Week 12", season="2024"),
    content_mix=ContentMix(highlights=1.0),
    requested_duration_minutes=120,
    loop_mode=LoopMode.single_playlist,
    exclusions=[],
    assumptions=[]
)
```

### Example 2: Complex Request

**Input**: "give me MLB in the first half then any random sports that had finals or big events and then top plays for games played Aug 8th 2010"

**Output**:
```python
HighlightRequestSpec(
    sport=Sport.MLB,
    leagues=[],
    teams=[],
    date_range=DateRange(single_date="2010-08-08"),
    content_mix=ContentMix(
        highlights=0.4,  # First half
        upsets=0.3,      # Finals/big events
        top_plays=0.3    # Top plays
    ),
    requested_duration_minutes=120,
    loop_mode=LoopMode.single_playlist,
    assumptions=[
        "Interpreted 'first half' as first portion of playlist (40% MLB highlights)",
        "Interpreted 'random sports that had finals or big events' as upsets/big events (30%)",
        "Assumed 2 hours duration for multi-sport request"
    ]
)
```

### Example 3: Duration Interpretation

**Input**: "Give me a full work day of random sports highlights"

**Output**:
```python
HighlightRequestSpec(
    sport=Sport.OTHER,
    requested_duration_minutes=480,  # 8 hours
    assumptions=[
        "Interpreted 'full work day' as 8 hours (480 minutes)",
        "Interpreted 'random sports' as no specific sport (OTHER)"
    ]
)
```

## Guardrails

### Hard Blocks

These requests are **immediately rejected**:

1. **Copyright Violations & YouTube Bypass Attempts**:
   - "full game reupload"
   - "reupload full game"
   - "pirated game"
   - "ppv reupload"
   - "pay per view reupload"
   - "download full game"
   - "download broadcast"
   - "pirate the whole broadcast"
   - "bypass youtube"
   - "download from youtube"
   - "youtube downloader"
   - "rip from youtube"
   - "extract from youtube"

2. **NSFW/Violent Content**:
   - "violence"
   - "fight compilation"
   - "worst injuries"
   - "brutal hits"
   - "nsfw"

### Soft Flags

These requests are **allowed but flagged**:

- "leaked"
- "unauthorized"
- "fan upload"
- "screen recording"

### Integration

Guardrails are checked **before** AI parsing:

```python
# 1. Normalize
normalized = normalize_sports_request(user_text)

# 2. Check guardrails
results = check_sports_highlight_guardrails(normalized)

# 3. Block if hard block
if has_hard_block_sports(results):
    return {"error": "Request blocked"}

# 4. Parse if passed
result = await parse_highlight_request(normalized)

# 5. Include flags in response
flags = summarize_sports_guardrails(results)
```

## System Prompt

The system prompt (`ai_prompts/sports_highlight_channel.md`) instructs the AI to:

1. **Parse user requests** into structured specs
2. **Handle ambiguity** with reasonable defaults
3. **Document assumptions** in the assumptions field
4. **Only ask for clarification** when truly necessary
5. **Output strict JSON** matching the schema

### Key Parsing Rules

- **Sports**: Handle ambiguous references (e.g., "football" → NFL or SOCCER based on context)
- **Dates**: Parse relative dates ("last Sunday", "yesterday") and convert to absolute dates
- **Duration**: Interpret phrases ("full work day" → 8 hours, "couple hours" → 2 hours)
- **Content Mix**: Distribute proportions for multiple content types
- **Exclusions**: Extract exclusion phrases ("no Jets", "no Super Bowl replays")

## Error Handling

- **JSON parsing errors**: Fallback to error response
- **Validation errors**: Return needs_clarification=true with questions
- **API errors**: Raise ValueError with descriptive message

## Future Enhancements

1. **Better date parsing**: Handle more relative date formats
2. **Team name normalization**: Handle variations ("KC Chiefs" vs "Kansas City Chiefs")
3. **Multi-sport support**: Better handling of sequential sport requests
4. **Confidence scoring**: More sophisticated confidence calculation
5. **Clarification questions**: Generate better follow-up questions

