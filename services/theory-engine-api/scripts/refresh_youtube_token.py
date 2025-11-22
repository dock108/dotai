#!/usr/bin/env python3
"""
Refresh YouTube OAuth access token using refresh token.

Usage:
    python scripts/refresh_youtube_token.py

    Or with environment variables:
    YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... YOUTUBE_REFRESH_TOKEN=... python scripts/refresh_youtube_token.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]


def load_dotenv_if_available() -> None:
    """Load the repo-level .env if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv

        env_path = ROOT_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


def main() -> None:
    # Ensure repo root is on path (not strictly needed here but keeps parity with other scripts)
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN") or os.getenv("YOUTUBE_OAUTH_REFRESH_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        print("❌ Missing required environment variables:")
        print("   - YOUTUBE_CLIENT_ID")
        print("   - YOUTUBE_CLIENT_SECRET")
        print("   - YOUTUBE_REFRESH_TOKEN (or YOUTUBE_OAUTH_REFRESH_TOKEN)")
        print("\n💡 Make sure these are set in your .env file or environment.")
        sys.exit(1)

    print("\n🔄 Refreshing YouTube OAuth Access Token\n")

    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )

        if not response.is_success:
            print(f"❌ Failed to refresh access token (status {response.status_code}):")
            print(response.text)
            sys.exit(1)

        tokens = response.json()

        if "access_token" not in tokens:
            print("❌ No access token in response:")
            print(tokens)
            sys.exit(1)

        print("✅ Success! New access token:\n")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("\n📝 Update your .env file with:\n")
        print(f"YOUTUBE_OAUTH_ACCESS_TOKEN={tokens['access_token']}")
        print("\n💡 Note: This token expires in 1 hour.")
        print("   Run this script again when needed, or set up automatic refresh.\n")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    except httpx.RequestError as exc:
        print(f"❌ Network error: {exc}")
        sys.exit(1)
    except Exception as exc:  # pragma: no cover - maintenance script
        print(f"❌ Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    load_dotenv_if_available()
    main()


