#!/usr/bin/env python3
"""
Refresh YouTube OAuth access token using refresh token.

Usage:
    python refresh_youtube_token.py
    
    Or with environment variables:
    YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... YOUTUBE_REFRESH_TOKEN=... python refresh_youtube_token.py
"""

import os
import sys
from urllib.parse import urlencode

import httpx


def main():
    # Get credentials from environment or .env file
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
    
    # Prepare token refresh request
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
        
    except httpx.RequestError as e:
        print(f"❌ Network error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Try to load .env file if python-dotenv is available
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
    except ImportError:
        pass  # python-dotenv not available, use environment variables only
    
    main()

