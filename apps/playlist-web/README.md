# Playlist Web

AI-curated YouTube playlist generator. Builds intentional playlists from natural language topics with configurable length, sports mode, and ending delay options.

## Quick Start

1. **Install dependencies** (from repo root):
   ```bash
   pnpm install
   ```

2. **Set up environment variables**:
   ```bash
   cd apps/playlist-web
   ```
   
   Create `.env.local` with:
   ```bash
   NEXT_PUBLIC_THEORY_ENGINE_URL=http://localhost:8000
   ```

3. **Start the development server**:
   ```bash
   pnpm dev
   ```

4. **Open your browser**:
   Navigate to http://localhost:3002

## Architecture

This app acts as a thin client that forwards requests to the `theory-engine-api` backend:

- **Frontend**: Next.js UI with query builder interface
- **API Route**: `/api/playlist` validates and forwards to `POST /api/theory/playlist`
- **Backend**: `theory-engine-api` handles all playlist curation logic:
  - Topic parsing and canonicalization
  - YouTube search and video filtering
  - Playlist sequencing and tagging
  - Optional YouTube playlist creation

The `legacy-mvp/` folder contains the original prototype for reference only.

### UX Notes

- Inputs: Topic text area, length dropdown, `Sports Mode → hide spoilers`, and (for 10+ hr requests) the “Keep the ending hidden” toggle with reveal timing options.
- Output: Playlist title, total runtime, ordered list with intro/context/deep dive/ending tags, lock indicators, and quick “Watch” links.
- “Save to YouTube” button appears once OAuth creds are provided; otherwise, the UI reminds you to drop in the token + channel id.
- “Regenerate with new vibe” simply re-runs the scoring pipeline with the same inputs.

## Features

- **Natural language input** - Describe any topic (e.g., "Lufthansa Heist but not Goodfellas")
- **Length buckets** - Choose from 5 min to 10+ hours
- **Sports mode** - Hide spoilers for sports content
- **Ending delay** - For long-form playlists, delay major reveals until specified time
- **Regeneration** - Re-run curation with same parameters for different results

## Development

The app uses:
- **Next.js 16** - React framework
- **TypeScript** - Type safety
- **@dock108/ui** - Shared UI components (DockHeader, DockFooter)
- **@dock108/ui-kit** - Shared form components (TheoryForm, PlaylistCard)
- **Zod** - Request validation

## Backend Integration

All playlist generation logic is handled by `theory-engine-api`:
- Topic parsing and enrichment
- YouTube search and video filtering
- Playlist sequencing and tagging
- Optional YouTube playlist creation

See `docs/PLAYLIST_API.md` for detailed backend API documentation.

### Testing Checklist

- ✅ Sports mode strips spoiler phrases in both titles and descriptions.
- ✅ Length buckets enforce ±20% runtime tolerance.
- ✅ 10+ hour requests surface the ending-delay question before submission.
- ✅ API gracefully degrades (returns playlist data even if YouTube playlist write fails).

### Future Enhancements

- Persist past playlists + allow quick reuse/shuffle weights.
- Add richer channel reputation heuristics + diversity controls.
- Support alternative vibes (interviews only, rabbit-hole heavy, etc.).

