# Highlights Web

Build your own sports highlight channel from natural language requests.

## Features

- **Natural language input** - Describe what you want in plain English
- **Quick presets** - One-click presets for common requests
- **Query builder** - Refine requests with sport chips, date ranges, duration sliders, and content mix
- **Playlist viewer** - View generated playlists with video details and scoring
- **Workday mode** - Background channel support (1h, 2h, 4h, 8h)
- **Transparency** - Explanation panel shows assumptions, filters, and ranking factors

## Usage

### Quick Start

1. **Select sports** - Choose one or more sports from the checklist
2. **Add filters** (optional) - Add up to 5 teams, players, or play types
3. **Choose time window** - Select from presets (Last 48 hours, Last 7 days, etc.) or custom range
4. **Set duration** - Use slider or presets (1h, 2h, 4h, 6h, 8h, 10h)
5. **Add comments** (optional) - Additional context for your request
6. **Build playlist** - Click "Build Highlight Show" and wait for results
7. **Watch on YouTube** - Click "Play Show on YouTube" to open the playlist

### Tips for Better Results

- **Be specific** - Include sport names, teams, players, or play types
- **Use recent dates** - The system works best for highlights from the last 48 hours to 30 days
- **Start broad** - Try a general query first, then refine with filters
- **Check the explanation** - See why videos were selected and how they were scored

### Common Issues

- **"No videos found"** - Try a broader search, adjust date range, or check spelling
- **"Rate limit exceeded"** - Wait a few minutes and try again
- **Long loading times** - Complex queries may take 30+ seconds

For detailed user guide, see [`docs/HIGHLIGHTS_USER_GUIDE.md`](../../docs/HIGHLIGHTS_USER_GUIDE.md).

## Development

```bash
cd apps/highlights-web
pnpm install
pnpm dev
```

Runs on port 3005.

## Environment Variables

Create a `.env.local` file:

```bash
# Backend API URL
NEXT_PUBLIC_THEORY_ENGINE_URL=http://localhost:8000
```

## API Integration

The app communicates with the theory-engine-api service:

- `POST /api/highlights/plan` - Plan a highlight playlist
- `GET /api/highlights/{playlist_id}` - Get playlist details
- `GET /api/highlights/metrics` - Get metrics (optional)

See `docs/HIGHLIGHTS_API.md` for detailed API documentation.

