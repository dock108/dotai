# API Keys Setup Guide

This guide explains how to obtain and configure all API keys needed for the dock108 theory engine.

## Required API Keys

### 1. OpenAI API Key (Required)

**Used for**: AI-powered theory analysis, query parsing, and content generation

**How to get it**:
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** in the left sidebar
4. Click **"Create new secret key"**
5. Give it a name (e.g., "dock108-theory-engine")
6. Copy the key immediately (you won't be able to see it again)
7. Add to `.env`:
   ```bash
   OPENAI_API_KEY=sk-proj-your-key-here
   ```

**Cost**: Pay-as-you-go. Check [OpenAI Pricing](https://openai.com/pricing) for current rates.

**Rate Limits**: Based on your tier. Free tier has lower limits.

---

### 2. YouTube Data API Key (Required for Highlights)

**Used for**: Searching YouTube videos, getting video metadata

**How to get it**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **"YouTube Data API v3"**:
   - Go to **APIs & Services** > **Library**
   - Search for "YouTube Data API v3"
   - Click on it and press **Enable**
4. Create credentials:
   - Go to **APIs & Services** > **Credentials**
   - Click **"Create Credentials"** > **API Key**
   - Copy the API key
5. (Optional but recommended) Restrict the API key:
   - Click on the API key to edit it
   - Under **API restrictions**, select **"Restrict key"**
   - Choose **"YouTube Data API v3"**
   - Save
6. Add to `.env`:
   ```bash
   YOUTUBE_API_KEY=AIzaSy-your-key-here
   ```

**Cost**: Free tier includes 10,000 units per day. See [YouTube Data API Quotas](https://developers.google.com/youtube/v3/getting-started#quota)

---

## Optional API Keys

### 3. Google Fact Check API Key (Optional - for Conspiracy Theory Evaluation)

**Used for**: Fact-checking conspiracy theories, getting verified ratings

**How to get it**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Use the same project as your YouTube API key (or create a new one)
3. Enable the **"Fact Check Tools API"**:
   - Go to **APIs & Services** > **Library**
   - Search for "Fact Check Tools API"
   - Click on it and press **Enable**
4. Create credentials:
   - Go to **APIs & Services** > **Credentials**
   - Click **"Create Credentials"** > **API Key**
   - Copy the API key
5. (Optional) Restrict the API key:
   - Click on the API key to edit it
   - Under **API restrictions**, select **"Restrict key"**
   - Choose **"Fact Check Tools API"**
   - Save
6. Add to `.env`:
   ```bash
   GOOGLE_FACTCHECK_API_KEY=your-google-factcheck-api-key-here
   ```

**Cost**: Free tier available. Check [Google Cloud Pricing](https://cloud.google.com/fact-check-tools/pricing) for details.

**Note**: The conspiracy theory evaluation works without this key, but fact-check results will be limited. Wikipedia results will still be available.

---

### 4. YouTube OAuth Credentials (Optional - for Playlist Creation)

**Used for**: Creating YouTube playlists, uploading videos

**How to get it**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Use the same project as your YouTube API key
3. Go to **APIs & Services** > **Credentials**
4. Click **"Create Credentials"** > **OAuth client ID**
5. If prompted, configure the OAuth consent screen:
   - Choose **External** (unless you have a Google Workspace)
   - Fill in required fields (App name, User support email, Developer contact)
   - Add scopes: `https://www.googleapis.com/auth/youtube.force-ssl`
   - Add test users if needed
6. Create OAuth client:
   - Application type: **Web application**
   - Name: "dock108-youtube-oauth"
   - Authorized redirect URIs: `http://localhost:8000/oauth/callback` (for local dev)
   - Click **Create**
7. Copy the **Client ID** and **Client Secret**
8. Add to `.env`:
   ```bash
   YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   YOUTUBE_CLIENT_SECRET=GOCSPX-your-client-secret
   ```

**Getting OAuth Tokens**:
- Use the `refresh_youtube_token.py` script in `services/theory-engine-api/scripts/`
- Or follow the OAuth flow manually (see `docs/YOUTUBE_SETUP.md`)

---

## Environment File Setup

All API keys should be added to `services/theory-engine-api/.env`:

```bash
# Required
OPENAI_API_KEY=sk-proj-your-key-here
YOUTUBE_API_KEY=AIzaSy-your-key-here

# Optional - Conspiracy Theory Evaluation
GOOGLE_FACTCHECK_API_KEY=your-google-factcheck-api-key-here

# Optional - Playlist Creation
YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-your-client-secret
YOUTUBE_OAUTH_ACCESS_TOKEN=ya29.your-access-token
YOUTUBE_OAUTH_REFRESH_TOKEN=1//your-refresh-token
YOUTUBE_PLAYLIST_CHANNEL_ID=UCyour-channel-id

# Optional - Watch Token Secret (for temporary playlist access links)
# Generate a secure random string: python -c "import secrets; print(secrets.token_urlsafe(32))"
WATCH_TOKEN_SECRET=your_random_32_plus_character_secret_here
```

## Security Best Practices

1. **Never commit `.env` files to git** - They're already in `.gitignore`
2. **Restrict API keys** - Use API restrictions in Google Cloud Console
3. **Rotate keys regularly** - Especially if they're exposed
4. **Use different keys for dev/prod** - Don't use production keys in development
5. **Monitor usage** - Set up billing alerts in Google Cloud Console

## Troubleshooting

### "API key not valid" error
- Check that the key is copied correctly (no extra spaces)
- Verify the API is enabled in Google Cloud Console
- Check that API restrictions allow the service you're using

### "Quota exceeded" error
- You've hit the daily quota limit
- Wait 24 hours or request a quota increase in Google Cloud Console
- For YouTube API, check your quota usage in the Cloud Console

### "Permission denied" error
- Check that the OAuth token has the correct scopes
- Verify the OAuth consent screen is configured
- Make sure you're using the correct client ID/secret

## Need Help?

- **OpenAI**: [OpenAI Help Center](https://help.openai.com/)
- **Google Cloud**: [Google Cloud Support](https://cloud.google.com/support)
- **YouTube API**: [YouTube API Documentation](https://developers.google.com/youtube/v3)

