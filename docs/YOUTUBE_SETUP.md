# YouTube OAuth Setup and Token Management

This guide covers setting up YouTube OAuth credentials and managing token refresh for playlist creation functionality.

## Overview

To enable playlist creation on YouTube, you need:
1. **OAuth 2.0 credentials** from Google Cloud Console
2. **Access token** for API calls (expires after 1 hour)
3. **Refresh token** to get new access tokens (long-lived)

## Part 1: Initial OAuth Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **YouTube Data API v3**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

### Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (unless you have a Google Workspace)
   - Fill in app name, user support email, developer contact
   - Add scopes: `https://www.googleapis.com/auth/youtube.force-ssl`
   - Add test users (your Google account) if in testing mode
4. Create OAuth client:
   - Application type: **Web application**
   - Name: "Dock108 Highlight Channel"
   - Authorized redirect URIs:
     - `http://localhost:8000/api/youtube/oauth/callback` (for local dev)
     - `https://your-domain.com/api/youtube/oauth/callback` (for production)
5. Save the **Client ID** and **Client Secret**

### Step 3: Configure Environment Variables

Add to `services/theory-engine-api/.env`:

```bash
YOUTUBE_CLIENT_ID=your_client_id_here
YOUTUBE_CLIENT_SECRET=your_client_secret_here
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/youtube/oauth/callback
```

### Step 4: Get Initial Authorization

1. Start the backend server
2. Visit the OAuth authorization URL (or use the `/api/youtube/oauth/authorize` endpoint)
3. Sign in with your Google account
4. Grant permissions for YouTube playlist creation
5. You'll be redirected back with an authorization code
6. The backend exchanges this for access and refresh tokens

## Part 2: Token Refresh

### Understanding Token Expiration

- **Access Token**: Expires after **1 hour** - used for API calls
- **Refresh Token**: Long-lived (doesn't expire unless revoked) - used to get new access tokens

### Automatic Refresh (Recommended)

The backend should automatically refresh tokens when they expire. The refresh flow:

1. When an access token expires, the backend detects the 401 error
2. Uses the stored refresh token to get a new access token
3. Updates the stored token
4. Retries the original request

### Manual Refresh

If you need to manually refresh tokens:

```bash
# Using the API endpoint (if implemented)
curl -X POST http://localhost:8000/api/youtube/oauth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token"}'
```

Or use the Google OAuth API directly:

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "grant_type=refresh_token"
```

### Storing Refresh Tokens

**Important**: Refresh tokens should be stored securely:
- **Never commit to git** - use environment variables or secure storage
- **Encrypt at rest** if storing in database
- **Rotate periodically** for security

For local development, you can store in `.env`:
```bash
YOUTUBE_REFRESH_TOKEN=your_refresh_token_here
```

For production, use a secure secrets manager (AWS Secrets Manager, Google Secret Manager, etc.).

## Troubleshooting

### "Invalid grant" error

- Refresh token may have been revoked
- User may have revoked access in Google Account settings
- Solution: Re-authorize to get a new refresh token

### "Access denied" error

- OAuth consent screen not properly configured
- Missing required scopes
- Solution: Check OAuth consent screen configuration and scopes

### Token expires too quickly

- Access tokens always expire after 1 hour (this is by design)
- Use refresh tokens to get new access tokens automatically
- Solution: Implement automatic token refresh in your backend

### Redirect URI mismatch

- The redirect URI in your OAuth client must match exactly
- Check for trailing slashes, http vs https, port numbers
- Solution: Verify redirect URI in Google Cloud Console matches your app

## Security Best Practices

1. **Never expose client secret** in frontend code
2. **Use HTTPS** in production for all OAuth flows
3. **Store refresh tokens securely** (encrypted, not in plain text)
4. **Rotate refresh tokens** periodically
5. **Monitor token usage** for suspicious activity
6. **Revoke tokens** if compromised

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [YouTube Data API v3 Documentation](https://developers.google.com/youtube/v3)
- [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) - For testing OAuth flows

