# Existing Apps & Scripts Inventory

> **Note**: This is a planning/inventory document from Phase 0. Some information may be outdated. For current app status, see `docs/ARCHITECTURE.md` and individual app READMEs.

This file captures today's runnable artifacts before we lift them into the refactored monorepo. Each entry summarizes how the code works now (inputs, outputs, API usage, persistence) plus the migration decision from Phase 0.

## AI Trainer Game (SwiftUI Prototype)

- **Location**: `apps/prompt-game-web/swift-prototype/ios-app`
- **Status**: Shipping SwiftUI app built around deterministic “lesson” puzzles backed by OpenAI chat completions.

### What it does today

- **Inputs**: Local `Resources/puzzles.json` lesson metadata (title, skill, scenario, solution) and player chat turns typed inside `PuzzlePlayView`.
- **Outputs**: Short GPT replies with `<GAME_PHASE>` tags (`LLMService`) rendered across `LaunchView`, `PuzzleListView`, `PuzzlePlayView`, plus share cards generated in `ShareCardView`.
- **External APIs**: `LLMService` posts to `https://api.openai.com/v1/chat/completions` with the prompt built by `SystemPromptBuilder`. API keys + preferred model are resolved via `SecretsProvider`.
- **Persistence / caching**: No remote storage yet. Puzzle progress lives in-memory inside `PuzzleStore`/`PuzzleViewModel`; player secrets live inside local `Secrets.plist`.

### Migration decision

- Keep the core puzzle/lesson logic and UX flows, but port them to React:
  - Move the deterministic state machine + prompt builder into `packages/js-core`.
  - Rebuild the UI in `apps/prompt-game-web` while we keep the Swift project compiling for TestFlight users until feature parity lands.

## YouTube Playlist Curator (Next.js)

- **Location**: `apps/playlist-web` (`legacy-mvp/` keeps the original prototype for reference).
- **Status**: Next.js App Router app with server actions + API routes powering the “topic → playlist” UX described in `apps/playlist-web/README.md`.

### What it does today

- **Inputs**: Topic free-text, desired runtime bucket, sports-mode toggle, spoiler/ending-protection toggles captured in `src/app/page.tsx`.
- **Outputs**: Structured playlist JSON (title, runtime, tagged segments, lock indicators) rendered in the client and optionally posted to YouTube as an unlisted playlist.
- **External APIs**:
  - OpenAI `gpt-4o-mini` for topic canonicalization, spoiler detection, and video tagging (`src/lib/topicParser.ts`, `videoClassifier.ts`).
  - YouTube Data API v3 for search + playlist writes (`src/lib/youtube.ts`, `youtubePlaylist.ts`).
- **Persistence / caching**: Currently stateless – data lives in-flight per request. OAuth tokens stored via `.env.local` and short-lived server memory; no database layer yet.

### Migration decision

- Preserve the ranking/filtering/sequence logic (to be extracted into `packages/js-core`), but port the UI to the shared React stack (Next.js/React Server Components) and lean on a Python backend (`services/theory-engine-api`) for API fan-out.
- Archive `legacy-mvp/` after we finish parity testing against the new pipeline.

## Odds / CCXT / Play-by-play Scripts

- **Location**: None checked into this repo yet; `services/data-workers` only contains planning docs.
- **Status**: No runnable oddsapi/ccxt/play-by-play scripts discovered via search; all related references live in `services/data-workers/README.md` and `docs/ROADMAP.md`.

### Migration decision

- Treat every one-off script as a worker inside `services/data-workers`:
  - `odds_snapshot.py` for oddsapi integrations.
  - `market_prices.py` for ccxt / exchange prices.
  - `play_by_play.py` (future) for sports telemetry.
- If we uncover additional ad-hoc scripts, either archive them in `docs/archive/` or fold them into the worker/service structure above so scheduling, logging, and guardrails stay consistent.


