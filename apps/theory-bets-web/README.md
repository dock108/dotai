# Theory Bets Web

Sports betting-focused UI powered by the shared theory engine.

## Quick Start

1. **Install dependencies** (from repo root):
   ```bash
   pnpm install
   ```

2. **Set up environment variables**:
   ```bash
   cd apps/theory-bets-web
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
   Navigate to http://localhost:3001

## Surfaces

- **Theory builder** (`/`) – submit betting theses and receive model feedback
- **Sports data admin** (`/admin/theory-bets/ingestion`) – configure and monitor boxscore/odds ingestion jobs
- **Boxscore viewer** (`/admin/boxscores`) – comprehensive game browser with advanced filtering, pagination, and detail views

## Development

The app uses:
- **Next.js 16** - React framework
- **TypeScript** - Type safety
- **@dock108/ui** - Shared UI components (DockHeader, DockFooter)
- **@dock108/ui-kit** - Shared form components (TheoryForm, TheoryCard)
- **@dock108/js-core** - Shared API client and hooks (useBetsEvaluation)

## Backend Integration

All theory evaluation and sports data management is handled by:
- **theory-engine-api** - Handles betting theory evaluation and sports data admin endpoints
- **theory-bets-scraper** - Celery workers for boxscore and odds ingestion

## Scripts

```bash
pnpm dev        # starts Next.js on port 3001
pnpm build      # build for production
pnpm start      # start production server
pnpm lint       # run ESLint
```

