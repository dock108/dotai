"""YouTube Data API client wrapper with authentication support."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


@dataclass
class VideoCandidate:
    """Candidate video from YouTube search."""

    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    duration_seconds: int
    published_at: datetime
    view_count: int
    thumbnail_url: str | None = None
    tags: list[str] | None = None


class YouTubeClient:
    """YouTube Data API client with search and playlist management.
    
    Supports both API key (read-only) and OAuth (read-write) authentication.
    """

    def __init__(
        self,
        api_key: str | None = None,
        oauth_token: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize YouTube client.
        
        Args:
            api_key: YouTube Data API key (for read-only operations)
            oauth_token: OAuth access token (for playlist creation)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.oauth_token = oauth_token or os.getenv("YOUTUBE_OAUTH_ACCESS_TOKEN")
        self.timeout = timeout
        
        if not self.api_key and not self.oauth_token:
            raise ValueError(
                "Either api_key or oauth_token must be provided, "
                "or set YOUTUBE_API_KEY or YOUTUBE_OAUTH_ACCESS_TOKEN env var"
            )

    async def search(
        self,
        query: str,
        max_results: int = 50,
        order: str = "relevance",
        video_duration: str | None = None,
        published_after: datetime | None = None,
    ) -> list[VideoCandidate]:
        """Search YouTube for videos.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (1-50)
            order: Sort order (relevance, date, rating, viewCount, title, videoCount)
            video_duration: Filter by duration (any, short, medium, long)
            published_after: Only return videos published after this date
        
        Returns:
            List of video candidates
        """
        if not self.api_key:
            raise ValueError("API key required for search operations")
        
        max_results = min(max_results, 50)
        
        params: dict[str, Any] = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "order": order,
            "key": self.api_key,
        }
        
        if video_duration:
            params["videoDuration"] = video_duration
        
        if published_after:
            params["publishedAfter"] = published_after.isoformat() + "Z"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            search_url = "https://www.googleapis.com/youtube/v3/search"
            response = await client.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            video_ids = [
                item["id"]["videoId"]
                for item in data.get("items", [])
                if "videoId" in item.get("id", {})
            ]
            
            if not video_ids:
                return []
            
            # Get detailed video information
            return await self.get_video_details(video_ids)

    async def get_video_details(self, video_ids: list[str]) -> list[VideoCandidate]:
        """Get detailed information for video IDs.
        
        Args:
            video_ids: List of YouTube video IDs (max 50)
        
        Returns:
            List of video candidates with full details
        """
        if not self.api_key:
            raise ValueError("API key required for video details")
        
        # YouTube API allows max 50 IDs per request
        chunks = [video_ids[i : i + 50] for i in range(0, len(video_ids), 50)]
        all_candidates: list[VideoCandidate] = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for chunk in chunks:
                params = {
                    "part": "snippet,contentDetails,statistics",
                    "id": ",".join(chunk),
                    "key": self.api_key,
                }
                
                videos_url = "https://www.googleapis.com/youtube/v3/videos"
                response = await client.get(videos_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    content_details = item.get("contentDetails", {})
                    statistics = item.get("statistics", {})
                    
                    # Parse duration
                    duration_str = content_details.get("duration", "PT0S")
                    duration_seconds = self._parse_iso_duration(duration_str)
                    
                    # Parse published date
                    published_str = snippet.get("publishedAt", "")
                    try:
                        published_at = datetime.fromisoformat(
                            published_str.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        published_at = datetime.utcnow()
                    
                    candidate = VideoCandidate(
                        video_id=item["id"],
                        title=snippet.get("title", ""),
                        description=snippet.get("description", ""),
                        channel_id=snippet.get("channelId", ""),
                        channel_title=snippet.get("channelTitle", ""),
                        duration_seconds=duration_seconds,
                        published_at=published_at,
                        view_count=int(statistics.get("viewCount", 0)),
                        thumbnail_url=(
                            snippet.get("thumbnails", {})
                            .get("default", {})
                            .get("url")
                        ),
                        tags=snippet.get("tags", []),
                    )
                    all_candidates.append(candidate)
        
        return all_candidates

    async def create_playlist(
        self,
        title: str,
        description: str,
        channel_id: str | None = None,
        privacy_status: str = "unlisted",
    ) -> str:
        """Create a YouTube playlist.
        
        Args:
            title: Playlist title
            description: Playlist description
            channel_id: Channel ID (optional, uses default if not provided)
            privacy_status: Privacy status (private, public, unlisted)
        
        Returns:
            Playlist ID
        """
        if not self.oauth_token:
            raise ValueError("OAuth token required for playlist creation")
        
        body = {
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": privacy_status},
        }
        
        if channel_id:
            body["snippet"]["channelId"] = channel_id
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status"
            headers = {
                "Authorization": f"Bearer {self.oauth_token}",
                "Content-Type": "application/json",
            }
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def add_video_to_playlist(
        self,
        playlist_id: str,
        video_id: str,
    ) -> str:
        """Add a video to a playlist.
        
        Args:
            playlist_id: YouTube playlist ID
            video_id: YouTube video ID
        
        Returns:
            Playlist item ID
        """
        if not self.oauth_token:
            raise ValueError("OAuth token required for playlist operations")
        
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet"
            headers = {
                "Authorization": f"Bearer {self.oauth_token}",
                "Content-Type": "application/json",
            }
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["id"]

    @staticmethod
    def _parse_iso_duration(duration_str: str) -> int:
        """Parse ISO 8601 duration string to seconds.
        
        Example: "PT15M33S" -> 933
        
        Args:
            duration_str: ISO 8601 duration string
        
        Returns:
            Duration in seconds
        """
        pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds

