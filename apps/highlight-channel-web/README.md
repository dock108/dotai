# Highlight Channel Web

Build your own sports highlight channel from natural language requests.

## Features

- **Natural language input** - Describe what you want in plain English
- **Quick presets** - One-click presets for common requests
- **Query builder** - Refine requests with sport chips, date ranges, duration sliders, and content mix
- **Playlist viewer** - View generated playlists with video details and scoring
- **Workday mode** - Background channel support (1h, 2h, 4h, 8h)
- **Transparency** - Explanation panel shows assumptions, filters, and ranking factors

## Usage

1. Enter a natural language request (e.g., "NFL Week 12 highlights, 2 hours")
2. Or click a preset chip
3. After first parse, query builder appears for refinement
4. View playlist with explanation panel
5. Use "Play All on YouTube" or workday mode buttons

## Development

```bash
cd apps/highlight-channel-web
pnpm install
pnpm dev
```

Runs on port 3005.

## Environment Variables

- `NEXT_PUBLIC_THEORY_ENGINE_URL` - Backend API URL (default: http://localhost:8000)

