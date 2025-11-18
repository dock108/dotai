"""Example usage of sports_search module."""

from datetime import datetime

from .sports_search import SportsSearchSpec, search_youtube_sports


async def example_nfl_highlights():
    """Example: Search for NFL Week 12 highlights."""
    spec = SportsSearchSpec(
        sport="NFL",
        league="NFL",
        date_range={"start": "2024-11-17", "end": "2024-11-24"},  # Week 12
        content_types=["highlights", "top plays"],
        duration_target_minutes=10,
    )
    
    candidates, _ = await search_youtube_sports(spec, max_results=20)
    
    print(f"Found {len(candidates)} candidate videos")
    for candidate in candidates[:5]:
        print(f"- {candidate.title} ({candidate.duration_seconds // 60}m)")
        print(f"  Channel: {candidate.channel_title}")
        print(f"  Views: {candidate.view_count:,}")
        print()


async def example_mlb_bloopers():
    """Example: Search for MLB bloopers."""
    spec = SportsSearchSpec(
        sport="MLB",
        league="MLB",
        content_types=["bloopers"],
        duration_target_minutes=5,
    )
    
    candidates = await search_youtube_sports(spec, max_results=15)
    
    print(f"Found {len(candidates)} blooper videos")
    for candidate in candidates[:5]:
        print(f"- {candidate.title}")


async def example_team_matchup():
    """Example: Search for specific team matchup."""
    spec = SportsSearchSpec(
        sport="NFL",
        teams=["Kansas City Chiefs", "Buffalo Bills"],
        date_range={"date": "2024-11-17"},
        content_types=["highlights", "condensed"],
        duration_target_minutes=15,
    )
    
    candidates = await search_youtube_sports(spec, max_results=10)
    
    print(f"Found {len(candidates)} videos for Chiefs vs Bills")
    for candidate in candidates:
        print(f"- {candidate.title} ({candidate.duration_seconds // 60}m)")


if __name__ == "__main__":
    import asyncio
    
    # Run examples
    asyncio.run(example_nfl_highlights())

