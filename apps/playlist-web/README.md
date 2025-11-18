## AI Curation MVP

> Lives inside the `dock108/apps/playlist-web` workspace of the monorepo. The `legacy-mvp/` folder keeps the earliest lightweight prototype for reference; the root Next.js project is the actively maintained build that will be upstreamed into the shared theory engine service.

Topic + length → intentional YouTube playlist. This MVP wires a simple UI to an orchestrated backend that:

- canonicalizes the requested topic with an LLM,
- searches YouTube for matching + filler videos,
- filters/grades the pool via lightweight rules,
- sequences the playlist (including 10+ hour “keep the ending hidden” logic), and
- optionally writes an unlisted playlist via a bot account.

### Stack

- Next.js App Router (UI + API route)
- OpenAI `gpt-4o-mini` for topic insights + tag classification
- YouTube Data API (search + playlist creation)
- Zod for request validation

### Setup

1. Copy `.env.example` → `.env.local` and fill in:

```bash
OPENAI_API_KEY=...
YOUTUBE_API_KEY=...

# Optional – needed for auto playlist creation
YOUTUBE_OAUTH_ACCESS_TOKEN=...
YOUTUBE_PLAYLIST_CHANNEL_ID=...
```

2. Install dependencies & run dev server:

```bash
npm install
npm run dev
```

3. Visit `http://localhost:3000`.

### UX Notes

- Inputs: Topic text area, length dropdown, `Sports Mode → hide spoilers`, and (for 10+ hr requests) the “Keep the ending hidden” toggle with reveal timing options.
- Output: Playlist title, total runtime, ordered list with intro/context/deep dive/ending tags, lock indicators, and quick “Watch” links.
- “Save to YouTube” button appears once OAuth creds are provided; otherwise, the UI reminds you to drop in the token + channel id.
- “Regenerate with new vibe” simply re-runs the scoring pipeline with the same inputs.

### Backend Flow

1. **Topic parsing** (`src/lib/topicParser.ts`) uses OpenAI with a JSON schema to return canonical topic, enrichment keywords, spoiler terms, and subtopics.
2. **Search + hydrate** (`src/lib/youtube.ts`) issues multiple Data API searches, then merges details.
3. **Filter + score** (`src/lib/videoFiltering.ts`) enforces keyword hits, runtime tolerance (±20%), spoiler/banned-term filters, and scores videos via simple heuristics.
4. **Video tagging** (`src/lib/videoClassifier.ts`) classifies each candidate (intro/context/deep dive/ending/misc) using the same LLM.
5. **Playlist planning** (`src/lib/playlistBuilder.ts`) assembles sequences per length bucket, inserts anchors for long runs, and annotates ending segments with lock thresholds when requested.
6. **Playlist creation** (`src/lib/youtubePlaylist.ts`) writes an unlisted playlist + items when OAuth credentials exist.

### Testing Checklist

- ✅ Sports mode strips spoiler phrases in both titles and descriptions.
- ✅ Length buckets enforce ±20% runtime tolerance.
- ✅ 10+ hour requests surface the ending-delay question before submission.
- ✅ API gracefully degrades (returns playlist data even if YouTube playlist write fails).

### Future Enhancements

- Persist past playlists + allow quick reuse/shuffle weights.
- Add richer channel reputation heuristics + diversity controls.
- Support alternative vibes (interviews only, rabbit-hole heavy, etc.).

