# YouTube OAuth Setup Guide

This guide walks you through setting up YouTube OAuth credentials to enable playlist creation functionality.

## Overview

YouTube OAuth allows the app to:
- Create playlists on your YouTube channel
- Add videos to playlists
- Manage playlist settings

**Note**: For basic video search (which the highlight channel uses), you only need a YouTube API key. OAuth is optional and only needed if you want to create playlists on YouTube.

## Prerequisites

- Google account with access to Google Cloud Console
- YouTube channel (can be a personal channel)
- YouTube Data API enabled in your Google Cloud project

## Step 1: Create OAuth 2.0 Credentials

### 1.1 Go to Google Cloud Console

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Make sure the **YouTube Data API v3** is enabled

### 1.2 Create OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** (unless you have a Google Workspace account)
3. Fill in required information:
   - **App name**: e.g., "Dock108 Sports Highlights"
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Click **Save and Continue**
5. On **Scopes** page, click **Add or Remove Scopes**
   - Add: `https://www.googleapis.com/auth/youtube.force-ssl`
   - Add: `https://www.googleapis.com/auth/youtube`
6. Click **Save and Continue**
7. On **Test users** (if External), add your Google account email
8. Click **Save and Continue**

### 1.3 Create OAuth Client ID

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Choose **Application type**: **Web application**
4. Name it: e.g., "Dock108 YouTube OAuth"
5. **Authorized redirect URIs**: Add:
   - `http://localhost` (for local development)
   - `http://localhost:3000` (if using a different port)
   - Your production domain if applicable
6. Click **Create**
7. **IMPORTANT**: Copy both:
   - **Client ID** (looks like: `123456789-abcdefghijklmnop.apps.googleusercontent.com`)
   - **Client secret** (looks like: `GOCSPX-abcdefghijklmnopqrstuvwxyz`)

Save these securely - you'll need them in the next step.

## Step 2: Get Your YouTube Channel ID

You need your YouTube channel ID to create playlists on your channel.

### Option A: From YouTube Studio

1. Go to [YouTube Studio](https://studio.youtube.com/)
2. Click **Settings** (gear icon) → **Channel** → **Advanced settings**
3. Your **Channel ID** is displayed at the bottom (format: `UC...`)

### Option B: From Your Channel URL

1. Go to your YouTube channel
2. Look at the URL: `https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxx`
3. The part after `/channel/` is your Channel ID

### Option C: Using YouTube API

```bash
# Using your API key
curl "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true&key=YOUR_API_KEY" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Step 3: Get OAuth Access Token

You have two options: use the provided script (easiest) or do it manually.

### Option A: Using the Provided Script (Recommended)

1. Navigate to the script location:
   ```bash
   cd apps/playlist-web
   ```

2. Run the script with your credentials:
   ```bash
   node scripts/get-youtube-token.js YOUR_CLIENT_ID YOUR_CLIENT_SECRET
   ```

   Or set environment variables:
   ```bash
   YOUTUBE_CLIENT_ID=your-client-id \
   YOUTUBE_CLIENT_SECRET=your-client-secret \
   node scripts/get-youtube-token.js
   ```

3. The script will:
   - Generate an authorization URL
   - Ask you to open it in your browser
   - Have you authorize the app
   - Extract the authorization code from the redirect URL
   - Exchange it for access and refresh tokens

4. Follow the prompts:
   - Open the authorization URL in your browser
   - Sign in with your Google account
   - Click "Allow" to grant permissions
   - You'll be redirected to `http://localhost?code=...`
   - Copy the **entire URL** from your browser (even if it shows an error)
   - Paste it into the script

5. The script will output:
   - `YOUTUBE_OAUTH_ACCESS_TOKEN=...` (expires in 1 hour)
   - `YOUTUBE_OAUTH_REFRESH_TOKEN=...` (use this to get new access tokens)

### Option B: Manual Process

#### Step 3.1: Get Authorization Code

1. Build the authorization URL:
   ```
   https://accounts.google.com/o/oauth2/v2/auth?
     client_id=YOUR_CLIENT_ID
     &redirect_uri=http://localhost
     &response_type=code
     &scope=https://www.googleapis.com/auth/youtube.force-ssl%20https://www.googleapis.com/auth/youtube
     &access_type=offline
     &prompt=consent
   ```

   Replace `YOUR_CLIENT_ID` with your actual client ID.

2. Open this URL in your browser
3. Sign in and authorize
4. You'll be redirected to `http://localhost?code=4/0A...`
5. Copy the `code` parameter value

#### Step 3.2: Exchange Code for Tokens

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "code=YOUR_AUTHORIZATION_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=http://localhost" \
  -d "grant_type=authorization_code"
```

Replace:
- `YOUR_AUTHORIZATION_CODE` with the code from step 3.1
- `YOUR_CLIENT_ID` with your OAuth client ID
- `YOUR_CLIENT_SECRET` with your OAuth client secret

Response will include:
```json
{
  "access_token": "ya29.a0AfH6SMC...",
  "expires_in": 3600,
  "refresh_token": "1//0g...",
  "scope": "https://www.googleapis.com/auth/youtube.force-ssl ...",
  "token_type": "Bearer"
}
```

## Step 4: Configure Environment Variables

Add these to your `services/theory-engine-api/.env` file:

```bash
# YouTube OAuth (for playlist creation)
YOUTUBE_OAUTH_ACCESS_TOKEN=ya29.a0AfH6SMC...your-access-token
YOUTUBE_OAUTH_REFRESH_TOKEN=1//0g...your-refresh-token
YOUTUBE_PLAYLIST_CHANNEL_ID=UCxxxxxxxxxxxxxxxxxxxxx
```

**Important Notes:**
- Access tokens expire after 1 hour
- Use the refresh token to get new access tokens when needed
- Keep these tokens secure - don't commit them to git

## Step 5: Refresh Access Token (When Needed)

Access tokens expire after 1 hour. Use the refresh token to get a new one:

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "grant_type=refresh_token"
```

This returns a new `access_token` (refresh token stays the same).

## Step 6: Verify Setup

Test that OAuth is working:

```bash
# Test getting channel info
curl "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

You should see your channel information.

## Troubleshooting

### "redirect_uri_mismatch" Error

- Make sure the redirect URI in your OAuth client matches exactly what you're using
- Common values: `http://localhost` or `http://localhost:3000`

### "invalid_grant" Error

- Authorization codes expire quickly (usually within minutes)
- Get a fresh authorization code and try again
- Make sure you're using the correct client ID and secret

### "access_denied" Error

- Make sure you clicked "Allow" when authorizing
- Check that your test user email is added in OAuth consent screen (if External app)

### Access Token Expired

- Access tokens expire after 1 hour
- Use the refresh token to get a new access token (see Step 5)

### Can't Find Channel ID

- Make sure you're signed in to the correct Google account
- Try the YouTube Studio method (most reliable)

## Security Best Practices

1. **Never commit tokens to git** - Use `.env` files (already in `.gitignore`)
2. **Rotate tokens periodically** - Regenerate if compromised
3. **Use environment-specific credentials** - Different OAuth clients for dev/prod
4. **Limit scopes** - Only request permissions you actually need
5. **Store refresh tokens securely** - They provide long-term access

## Next Steps

Once OAuth is configured, the app can:
- Create playlists on your YouTube channel
- Add videos to playlists
- Set playlist privacy settings

The highlight channel feature will work with just the API key for searching, but OAuth enables the full playlist creation experience.

