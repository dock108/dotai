"""Watch token generation and validation for temporary playlist access."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

# Get secret key from environment, fallback to a default for development
WATCH_TOKEN_SECRET = os.getenv("WATCH_TOKEN_SECRET", "dev-secret-key-change-in-production-min-32-chars")
TOKEN_EXPIRATION_HOURS = 48


def generate_watch_token(playlist_id: int) -> str:
    """Generate a signed JWT token for temporary playlist access.
    
    Args:
        playlist_id: The playlist ID to grant access to
    
    Returns:
        Signed JWT token string
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=TOKEN_EXPIRATION_HOURS)
    
    payload: dict[str, Any] = {
        "playlist_id": playlist_id,
        "expires_at": expires_at.isoformat(),
        "iat": now.isoformat(),  # issued at
    }
    
    token = jwt.encode(payload, WATCH_TOKEN_SECRET, algorithm="HS256")
    return token


def validate_watch_token(token: str) -> dict[str, Any] | None:
    """Validate and decode a watch token.
    
    Args:
        token: JWT token string to validate
    
    Returns:
        Decoded payload dict if valid and not expired, None otherwise
    """
    try:
        payload = jwt.decode(token, WATCH_TOKEN_SECRET, algorithms=["HS256"])
        
        # Check expiration
        expires_at_str = payload.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if expires_at < now:
                return None  # Token expired
        
        return payload
    except jwt.InvalidTokenError:
        return None  # Invalid token

