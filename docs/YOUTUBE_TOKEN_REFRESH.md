# YouTube OAuth Token Refresh Guide

## Understanding Token Expiration

- **Access Token**: Expires after **1 hour** - used for API calls
- **Refresh Token**: **Never expires** (unless revoked) - used to get new access tokens

## Quick Refresh Options

### Option 1: Manual Refresh Script (Easiest)

I've created a script to refresh your token:

```bash
cd apps/playlist-web
node scripts/refresh-youtube-token.js
```

The script will automatically read from your `.env` file if you have these set:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`  
- `YOUTUBE_OAUTH_REFRESH_TOKEN`

Or pass them directly:
```bash
node scripts/refresh-youtube-token.js YOUR_CLIENT_ID YOUR_CLIENT_SECRET YOUR_REFRESH_TOKEN
```

The script will output the new access token - just update `YOUTUBE_OAUTH_ACCESS_TOKEN` in your `.env` file.

### Option 2: Manual cURL Command

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "grant_type=refresh_token"
```

Replace the values from your `.env` file. Response will include a new `access_token`.

### Option 3: Automatic Refresh (Future Enhancement)

For production, you'd want automatic token refresh. This would:
1. Check if token is expired before API calls
2. Automatically refresh using the refresh token
3. Update the token in memory/cache

This isn't implemented yet, but could be added to `YouTubeClient` in `packages/py-core/py_core/clients/youtube.py`.

## When to Refresh

**You need to refresh when:**
- Access token expires (after 1 hour of use)
- You get a `401 Unauthorized` error from YouTube API
- Starting a new session after the token has expired

**You DON'T need to refresh:**
- If you're just searching videos (uses API key, not OAuth)
- If the token is still valid (less than 1 hour old)
- For read-only operations (API key is sufficient)

## Current Setup

Your `.env` file now has:
- ✅ `YOUTUBE_OAUTH_ACCESS_TOKEN` - Current access token (expires in 1 hour)
- ✅ `YOUTUBE_OAUTH_REFRESH_TOKEN` - Refresh token (never expires)
- ✅ `YOUTUBE_CLIENT_ID` - OAuth client ID
- ✅ `YOUTUBE_CLIENT_SECRET` - OAuth client secret

## Recommended Workflow

1. **For development/testing**: 
   - Use the refresh script when you get a 401 error
   - Or refresh manually every hour if doing extended testing

2. **For production** (when implemented):
   - Add automatic refresh logic to `YouTubeClient`
   - Store tokens securely (environment variables or secret manager)
   - Refresh proactively before expiration

## Testing Token Refresh

```bash
# Test current token
curl "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# If you get 401, refresh:
cd apps/playlist-web
node scripts/refresh-youtube-token.js
```

## Notes

- **Refresh tokens are long-lived** - save them securely
- **Access tokens are short-lived** - refresh as needed
- **API key works for search** - OAuth only needed for playlist creation
- **Don't commit tokens to git** - they're already in `.gitignore`

