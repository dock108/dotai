# Conspiracy Theory Evaluation App

A Next.js frontend for evaluating conspiracy theories with narrative-driven analysis, evidence comparison, and rubric-based confidence scoring.

## Quick Start

1. **Install dependencies** (from repo root):
   ```bash
   pnpm install
   ```

2. **Set up environment variables**:
   ```bash
   cd apps/theory-conspiracy-web
   cp .env.local.example .env.local
   ```
   
   Edit `.env.local` and set:
   ```bash
   NEXT_PUBLIC_THEORY_ENGINE_URL=http://localhost:8000
   ```

3. **Start the development server**:
   ```bash
   pnpm dev
   ```

4. **Open your browser**:
   Navigate to http://localhost:3004

## Environment Variables

### Required

- `NEXT_PUBLIC_THEORY_ENGINE_URL` - URL of the backend API server
  - Local development: `http://localhost:8000`
  - Production: Your deployed API URL

## Features

The app provides narrative-driven conspiracy theory analysis with:

- **The Claim** - One-sentence reframing of the user's query
- **The Story Behind This Theory** - 4-7 paragraph mini-documentary covering:
  - Origin and historical context
  - Public interest and cultural impact
  - Proponents and their arguments
  - Anomalies and debunking attempts
  - Turning points in the theory's evolution
- **Claims vs Evidence** - Side-by-side comparison of specific claims against available evidence
- **Final Verdict** - Direct, evidence-based conclusion
- **Confidence Score (0-100)** - Rubric-based scoring using:
  - Historical documentation (30%)
  - Independent corroboration (20%)
  - Scientific plausibility (20%)
  - Expert consensus (20%)
  - Internal coherence (10%)
- **Sources Consulted** - Human-readable list of sources (Wikipedia, fact-check databases, etc.)
- **What Fuels This Theory Today?** - Optional section on how the theory persists in culture

## Development

The app uses:
- **Next.js 16** - React framework
- **TypeScript** - Type safety
- **@dock108/ui-kit** - Shared UI components (including `TheoryCard` with narrative display)
- **@dock108/js-core** - Shared API client and types

## Backend Requirements

Make sure the backend API is running at the URL specified in `NEXT_PUBLIC_THEORY_ENGINE_URL`.

The backend fetches context from:
- Wikipedia REST API (for article summaries and key facts)
- Google Fact Check Explorer API (optional, for fact-check ratings)

See `docs/LOCAL_DEPLOY.md` for full setup instructions and `docs/CONSPIRACY_THEORY.md` for detailed feature documentation.
