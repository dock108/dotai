"""Helper functions for playlist query normalization and signature generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any

from .db_models import PlaylistMode


@dataclass
class PlaylistQuerySpec:
    """Structured specification for a playlist query."""

    sport: str | None = None
    leagues: list[str] | None = None
    teams: list[str] | None = None
    date_range: dict[str, Any] | None = None  # e.g., {"start": "2024-11-01", "end": "2024-11-18"}
    mix: list[str] | None = None  # e.g., ["highlights", "bloopers", "upsets"]
    duration_bucket: str | None = None  # e.g., "30_60", "60_180"
    exclusions: list[str] | None = None
    language: str = "en"
    mode: PlaylistMode = PlaylistMode.general_playlist


def generate_normalized_signature(spec: PlaylistQuerySpec) -> str:
    """Generate a normalized hash signature from a query spec.
    
    This signature is used to identify equivalent queries for caching purposes.
    Two queries with the same normalized signature should return the same playlist
    (unless the playlist is stale or schema version has changed).
    
    Args:
        spec: Structured playlist query specification
    
    Returns:
        SHA-256 hash of the normalized spec (64 character hex string)
    """
    # Convert spec to dict and normalize
    spec_dict = asdict(spec)
    
    # Normalize lists by sorting (for consistent hashing)
    for key in ["leagues", "teams", "mix", "exclusions"]:
        if spec_dict.get(key):
            spec_dict[key] = sorted(spec_dict[key])
    
    # Normalize date_range if present
    if spec_dict.get("date_range"):
        # Sort date range keys for consistency
        spec_dict["date_range"] = dict(sorted(spec_dict["date_range"].items()))
    
    # Convert to JSON string with sorted keys
    spec_json = json.dumps(spec_dict, sort_keys=True, default=str)
    
    # Generate SHA-256 hash
    return hashlib.sha256(spec_json.encode()).hexdigest()


def parse_query_to_spec(query_text: str, mode: PlaylistMode = PlaylistMode.general_playlist) -> PlaylistQuerySpec:
    """Parse raw query text into structured spec.
    
    This is a placeholder - in production, this would use LLM or NLP to extract:
    - Sport (NFL, MLB, NBA, etc.)
    - Leagues
    - Teams
    - Date ranges
    - Mix types (highlights, bloopers, upsets)
    - Exclusions
    
    Args:
        query_text: Raw user input (e.g., "NFL Week 12 highlights and MLB bloopers")
        mode: Playlist mode
    
    Returns:
        Structured query specification
    """
    # Note: LLM-based parsing is implemented in highlight_parser.py
    # This function is kept for backward compatibility but delegates to highlight_parser
    # For now, return a basic spec
    return PlaylistQuerySpec(
        mode=mode,
        language="en",
    )

