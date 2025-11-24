# Theory Crypto Web

Crypto strategy interpreter for dock108. Describe a pattern → get a structured strategy packet, backtest blueprint, and alert wiring.

## Quick Start

1. **Install dependencies** (from repo root):
   ```bash
   pnpm install
   ```

2. **Set up environment variables**:
   ```bash
   cd apps/theory-crypto-web
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
   Navigate to http://localhost:3005/strategy

## Stack

- **Next.js 16** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Component primitives (Radix UI)
- **Zustand** - Lightweight state management
- **@dock108/ui** - Shared UI components (DockHeader, DockFooter)
- **@dock108/js-core** - Shared API client and types
- **theory-engine-api** - Backend API handles all server-side operations

## Environment

The app requires the `theory-engine-api` backend to be running. Set:

```
NEXT_PUBLIC_THEORY_ENGINE_URL=http://localhost:8000
```

All backend environment variables (database, OpenAI API key, etc.) are configured in the root `.env` file.

## 4. Repo layout

```
src/
  app/
    strategy/                    # Builder + detail UI
      components/                # StrategyCard, JSON viewer, panels
      [id]/                      # Detail page + client shell
  lib/
    api/                         # API client (calls theory-engine-api)
    utils/                       # validators + ids + helpers
  store/                         # Zustand store for builder state
  components/                    # Theme, footer, shadcn primitives
  styles/                        # CSS tokens
```

## 5. Flow overview

1. `/strategy` — input textarea + chips → calls `theory-engine-api` endpoints via `@dock108/js-core`.
2. Backend handles interpretation, validation, Postgres persistence, backtesting, and alerts.
3. UI shows accordion preview + Save / Backtest / Alerts controls.
4. All server-side operations (LLM calls, DB writes, backtest execution) happen in `theory-engine-api`.
5. Frontend is a thin client that displays results and manages UI state.

## 6. QA script

1. `pnpm dev` then `http://localhost:3005/strategy`.
2. Fire the sample prompts (BTC CPI dip, ETH gas < 20, SOL OI spike, BTC + ETF inflow).
3. Confirm interpretation → JSON viewer → diagnostics → alert spec all populate.
4. Hit *Save Strategy* and verify success toast.
5. Run *Backtest* — metrics + spark bars appear.
6. Toggle alerts on/off and refresh events (synthetic events appear unless Postgres alerts exist).
7. Visit `/strategy/{id}` (grab the ID from the toast or network tab) and repeat: overview/backtest/alerts tabs, run backtest, toggle alerts.
8. Regression:
   - Submit < 10 characters → validation message.
   - Paste a long paragraph.
   - Save multiple strategies (verify rows in `strategies` table).
   - Inspect JSON viewer formatting + accordion motion.

## 7. Backend Requirements

Make sure `theory-engine-api` is running at the URL specified in `NEXT_PUBLIC_THEORY_ENGINE_URL`.

The backend handles:
- Strategy interpretation (LLM calls)
- Database persistence (Postgres)
- Backtest execution
- Alert management

Database tables are managed by `theory-engine-api` migrations. See `services/theory-engine-api/README.md` for database setup.
