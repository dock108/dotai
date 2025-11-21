"""AI-powered video description analyzer for relevance and quality checking."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass
class DescriptionAnalysis:
    """Analysis result for a video description."""
    
    is_relevant: bool  # Matches query criteria
    is_high_quality: bool  # Official/legitimate content
    confidence: float  # 0.0-1.0
    extracted_metadata: dict[str, Any]  # Game date, teams, play types, etc.
    rejection_reason: str | None = None  # Why it failed if rejected


async def analyze_video_description(
    title: str,
    description: str,
    channel_title: str,
    query_spec: dict[str, Any],
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
) -> DescriptionAnalysis:
    """Analyze video description for relevance and quality.
    
    Args:
        title: Video title
        description: Video description
        channel_title: Channel name
        query_spec: Dictionary with query details (players, play_types, sport, date_range, teams)
        api_key: OpenAI API key (or from env)
        model: OpenAI model to use
    
    Returns:
        DescriptionAnalysis with relevance, quality, and metadata
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key required (set OPENAI_API_KEY env var)")
    
    client = OpenAI(api_key=api_key)
    
    # Build query context for analysis
    query_context = {
        "sport": query_spec.get("sport", ""),
        "players": query_spec.get("players", []),
        "play_types": query_spec.get("play_types", []),
        "teams": query_spec.get("teams", []),
        "date_range": query_spec.get("date_range"),
    }
    
    system_prompt = """You are a sports video content analyzer. Your job is to analyze video descriptions and determine:
1. Relevance: Does this video match the user's query criteria (player, play type, date, team)?
2. Quality: Is this official/legitimate content or fan-edited content with music/overlays?

Return ONLY valid JSON matching this structure:
{
  "is_relevant": true/false,
  "is_high_quality": true/false,
  "confidence": 0.0-1.0,
  "extracted_metadata": {
    "game_date": "YYYY-MM-DD or null",
    "teams": ["team1", "team2"] or null,
    "play_types": ["touchdown", "interception"] or null,
    "players": ["player name"] or null
  },
  "rejection_reason": "reason string or null"
}

Quality indicators:
- Official content: Official league/team channels, major networks (ESPN, CBS Sports, NFL Network)
- Low quality: Fan edits, music overlays, compilations with heavy editing, "with music" in title
- High quality: Official broadcasts, game highlights from official sources, mic'd up content

Relevance indicators:
- Player names must match (or last name match)
- Play types must be the MAIN FOCUS of the video (not just mentioned in passing)
  - For "interceptions and fumbles": video should be specifically about interceptions/fumbles, not general game highlights
  - Look for keywords like "compilation", "highlights", "best plays" combined with the play type
  - Reject general "game highlights" if play types are specified - user wants play-type-specific content
- Dates should be within the specified range
- Teams should match if specified

CRITICAL: If play types are specified (e.g., "interceptions", "fumbles"), the video MUST be primarily about those play types, not general game highlights.

RECENCY CHECK: If the date range is recent (last 2-30 days), reject videos that are:
- Season recaps or "best of season" compilations
- "Top 10" or "best plays" that span multiple weeks/months
- Historical retrospectives or "throwback" content
- Videos that mention dates outside the requested window in the title/description

For recent highlights catch-up, prioritize videos that are:
- Game-specific highlights from the date range
- Week-specific recaps (e.g., "Week 9 highlights")
- Recent uploads that match the exact time window requested"""
    
    user_prompt = f"""Analyze this video:

Title: {title}
Channel: {channel_title}
Description: {description[:1000]}  # Truncate to avoid token limits

User Query Criteria:
- Sport: {query_context['sport']}
- Players: {', '.join(query_context.get('players', [])) or 'None specified'}
- Play Types: {', '.join(query_context.get('play_types', [])) or 'None specified'}
- Teams: {', '.join(query_context.get('teams', [])) or 'None specified'}
- Date Range: {str(query_context.get('date_range', 'None specified'))}

Determine if this video is:
1. Relevant to the query (matches player/play type/date/team criteria)
2. High quality (official content, not fan edits with music/overlays)

Return ONLY valid JSON, no markdown, no explanations."""
    
    try:
        # Run OpenAI call in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # Low temperature for consistent analysis
                response_format={"type": "json_object"},
            )
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        # Parse JSON response
        parsed_data = json.loads(content)
        
        return DescriptionAnalysis(
            is_relevant=parsed_data.get("is_relevant", False),
            is_high_quality=parsed_data.get("is_high_quality", False),
            confidence=float(parsed_data.get("confidence", 0.5)),
            extracted_metadata=parsed_data.get("extracted_metadata", {}),
            rejection_reason=parsed_data.get("rejection_reason"),
        )
    except json.JSONDecodeError as e:
        # If JSON parsing fails, return conservative analysis
        return DescriptionAnalysis(
            is_relevant=False,
            is_high_quality=False,
            confidence=0.0,
            extracted_metadata={},
            rejection_reason=f"Analysis failed: {str(e)}",
        )
    except Exception as e:
        # On any error, return conservative analysis
        return DescriptionAnalysis(
            is_relevant=False,
            is_high_quality=False,
            confidence=0.0,
            extracted_metadata={},
            rejection_reason=f"Analysis error: {str(e)}",
        )


async def analyze_video_descriptions_batch(
    videos: list[dict[str, Any]],
    query_spec: dict[str, Any],
    batch_size: int = 15,
    api_key: str | None = None,
) -> list[tuple[dict[str, Any], DescriptionAnalysis]]:
    """Analyze multiple video descriptions in batches.
    
    Args:
        videos: List of video dicts with title, description, channel_title
        query_spec: Query specification for analysis
        batch_size: Number of videos to analyze per batch
        api_key: OpenAI API key
    
    Returns:
        List of tuples (video, analysis) for all videos
    """
    results = []
    
    # Process in batches to manage API costs and rate limits
    for i in range(0, len(videos), batch_size):
        batch = videos[i:i + batch_size]
        batch_tasks = []
        
        for video in batch:
            task = analyze_video_description(
                title=video.get("title", ""),
                description=video.get("description", ""),
                channel_title=video.get("channel_title", ""),
                query_spec=query_spec,
                api_key=api_key,
            )
            batch_tasks.append((video, task))
        
        # Process batch concurrently
        import asyncio
        batch_results = await asyncio.gather(*[task for _, task in batch_tasks], return_exceptions=True)
        
        for (video, _), analysis in zip(batch_tasks, batch_results):
            if isinstance(analysis, Exception):
                # On error, create conservative analysis
                analysis = DescriptionAnalysis(
                    is_relevant=False,
                    is_high_quality=False,
                    confidence=0.0,
                    extracted_metadata={},
                    rejection_reason=f"Analysis exception: {str(analysis)}",
                )
            results.append((video, analysis))
    
    return results

