#!/usr/bin/env node

/**
 * Refresh YouTube OAuth access token using refresh token
 * 
 * Usage:
 *   node scripts/refresh-youtube-token.js YOUR_CLIENT_ID YOUR_CLIENT_SECRET YOUR_REFRESH_TOKEN
 * 
 * Or set environment variables:
 *   YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... YOUTUBE_OAUTH_REFRESH_TOKEN=... node scripts/refresh-youtube-token.js
 */

const CLIENT_ID = process.env.YOUTUBE_CLIENT_ID || process.argv[2];
const CLIENT_SECRET = process.env.YOUTUBE_CLIENT_SECRET || process.argv[3];
const REFRESH_TOKEN = process.env.YOUTUBE_OAUTH_REFRESH_TOKEN || process.argv[4];

if (!CLIENT_ID || !CLIENT_SECRET || !REFRESH_TOKEN) {
  console.error('❌ Missing client ID, secret, or refresh token');
  console.error('\nUsage:');
  console.error('  node scripts/refresh-youtube-token.js YOUR_CLIENT_ID YOUR_CLIENT_SECRET YOUR_REFRESH_TOKEN');
  console.error('\nOr set environment variables:');
  console.error('  YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... YOUTUBE_OAUTH_REFRESH_TOKEN=... node scripts/refresh-youtube-token.js');
  process.exit(1);
}

async function main() {
  console.log('\n🔄 Refreshing YouTube OAuth Access Token\n');
  
  const tokenData = new URLSearchParams({
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
    refresh_token: REFRESH_TOKEN,
    grant_type: 'refresh_token',
  });

  try {
    const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: tokenData.toString(),
    });

    if (!tokenResponse.ok) {
      const error = await tokenResponse.text();
      console.error('❌ Failed to refresh access token:');
      console.error(error);
      process.exit(1);
    }

    const tokens = await tokenResponse.json();

    console.log('✅ Success! New access token:\n');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('\n📝 Update your .env file with:\n');
    console.log(`YOUTUBE_OAUTH_ACCESS_TOKEN=${tokens.access_token}`);
    console.log('\n💡 Note: This token expires in 1 hour.');
    console.log('   Run this script again when needed, or set up automatic refresh.\n');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();

