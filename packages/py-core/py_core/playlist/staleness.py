"""Staleness computation for playlist caching based on event recency."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def compute_stale_after(
    event_date: datetime | None,
    now: datetime,
    mode: str = "sports_highlight",
) -> datetime | None:
    """Compute when a playlist should be considered stale based on event recency.
    
    Rules:
    - For events < 2 days old: stale_after = created_at + 6 hours
    - For 2-30 days old: stale_after = created_at + 3 days
    - For >30 days old: basically never re-fetch unless forced (returns None)
    
    Args:
        event_date: The date of the sports event (or None for general playlists)
        now: Current timestamp (typically when playlist is created)
        mode: Playlist mode ("sports_highlight" or "general_playlist")
    
    Returns:
        Timestamp when playlist becomes stale, or None if it should never expire
    """
    # Normalize now to timezone-aware (UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    
    # Normalize event_date if provided
    if event_date is not None:
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        else:
            event_date = event_date.astimezone(timezone.utc)
    
    # For general playlists without event dates, use a default 7-day TTL
    if event_date is None:
        if mode == "general_playlist":
            return now + timedelta(days=7)
        # For sports highlights without event date, use conservative 1-day TTL
        return now + timedelta(days=1)

    # Calculate age of event
    age = now - event_date

    # Events < 2 days old: refresh every 6 hours
    if age < timedelta(days=2):
        return now + timedelta(hours=6)

    # Events 2-30 days old: refresh every 3 days
    if age < timedelta(days=30):
        return now + timedelta(days=3)

    # Events >30 days old: never expire (unless manually refreshed or schema version changes)
    return None


def is_stale(stale_after: datetime | None, now: datetime) -> bool:
    """Check if a playlist is stale.
    
    Args:
        stale_after: Timestamp when playlist becomes stale (None = never expires)
        now: Current timestamp
    
    Returns:
        True if playlist is stale, False otherwise
    """
    if stale_after is None:
        return False
    
    # Normalize both datetimes to timezone-aware (UTC) for comparison
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    
    if stale_after.tzinfo is None:
        stale_after = stale_after.replace(tzinfo=timezone.utc)
    else:
        stale_after = stale_after.astimezone(timezone.utc)
    
    return now >= stale_after


def should_refresh_playlist(
    playlist_created_at: datetime,
    stale_after: datetime | None,
    now: datetime,
    force_refresh: bool = False,
    schema_version_changed: bool = False,
) -> bool:
    """Determine if a playlist should be refreshed.
    
    Args:
        playlist_created_at: When the playlist was created
        stale_after: When the playlist becomes stale (None = never expires)
        now: Current timestamp
        force_refresh: Manual refresh flag
        schema_version_changed: Whether the parsing/scoring schema has changed
    
    Returns:
        True if playlist should be refreshed
    """
    # Always refresh if forced
    if force_refresh:
        return True

    # Always refresh if schema version changed
    if schema_version_changed:
        return True

    # Check if stale
    return is_stale(stale_after, now)

