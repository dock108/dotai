#!/usr/bin/env node

/**
 * Simple script to get YouTube OAuth access token
 * 
 * Usage:
 *   node scripts/get-youtube-token.js YOUR_CLIENT_ID YOUR_CLIENT_SECRET
 * 
 * Or set environment variables:
 *   YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... node scripts/get-youtube-token.js
 */

const readline = require('readline');
const https = require('https');

const CLIENT_ID = process.env.YOUTUBE_CLIENT_ID || process.argv[2];
const CLIENT_SECRET = process.env.YOUTUBE_CLIENT_SECRET || process.argv[3];

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error('❌ Missing client ID or secret');
  console.error('\nUsage:');
  console.error('  node scripts/get-youtube-token.js YOUR_CLIENT_ID YOUR_CLIENT_SECRET');
  console.error('\nOr set environment variables:');
  console.error('  YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... node scripts/get-youtube-token.js');
  process.exit(1);
}

// Required scopes for creating playlists
const SCOPES = [
  'https://www.googleapis.com/auth/youtube.force-ssl',
  'https://www.googleapis.com/auth/youtube',
].join(' ');

// Redirect URI - using localhost (simplest for web app OAuth clients)
const REDIRECT_URI = 'http://localhost';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function question(prompt) {
  return new Promise((resolve) => {
    rl.question(prompt, resolve);
  });
}

async function main() {
  console.log('\n🔐 YouTube OAuth Token Generator\n');
  
  // Step 1: Generate authorization URL
  const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
  authUrl.searchParams.set('client_id', CLIENT_ID);
  authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('scope', SCOPES);
  authUrl.searchParams.set('access_type', 'offline'); // Get refresh token
  authUrl.searchParams.set('prompt', 'consent'); // Force consent to get refresh token

  console.log('📋 Step 1: Authorize the application');
  console.log('\nOpen this URL in your browser:');
  console.log('\n' + authUrl.toString() + '\n');
  console.log('After authorizing, you will be redirected to:');
  console.log(`  ${REDIRECT_URI}?code=4/0A...&scope=...`);
  console.log('\nThe page may show "This site can\'t be reached" - that\'s OK!');
  console.log('Just copy the ENTIRE URL from your browser address bar.\n');

  const redirectUrl = await question('Paste the redirect URL here: ');

  // Extract authorization code from redirect URL
  let code;
  try {
    const url = new URL(redirectUrl);
    code = url.searchParams.get('code');
  } catch {
    // If it's not a valid URL, maybe they just pasted the code
    code = redirectUrl.trim();
  }

  if (!code) {
    console.error('❌ No authorization code found. Make sure you copied the full URL.');
    process.exit(1);
  }

  console.log('\n🔄 Step 2: Exchanging code for access token...\n');

  // Step 2: Exchange code for access token
  const tokenData = new URLSearchParams({
    code,
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
    redirect_uri: REDIRECT_URI,
    grant_type: 'authorization_code',
  });

  const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: tokenData.toString(),
  });

  if (!tokenResponse.ok) {
    const error = await tokenResponse.text();
    console.error('❌ Failed to get access token:');
    console.error(error);
    process.exit(1);
  }

  const tokens = await tokenResponse.json();

  console.log('✅ Success! Here are your tokens:\n');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('\n📝 Add this to your .env.local file:\n');
  console.log(`YOUTUBE_OAUTH_ACCESS_TOKEN=${tokens.access_token}`);
  
  if (tokens.refresh_token) {
    console.log(`\n💾 Refresh token (save this for later):`);
    console.log(`YOUTUBE_OAUTH_REFRESH_TOKEN=${tokens.refresh_token}`);
    console.log('\n💡 Note: Access tokens expire after 1 hour.');
    console.log('   Use the refresh token to get a new access token when needed.');
  }
  
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  rl.close();
}

main().catch((error) => {
  console.error('❌ Error:', error.message);
  process.exit(1);
});

