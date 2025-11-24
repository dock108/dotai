# Prompt Game Web

Interactive AI prompting training game. Learn to write effective prompts through structured lessons with real-time feedback and scoring.

## Quick Start

1. **Install dependencies** (from repo root):
   ```bash
   pnpm install
   ```

2. **Set up environment variables**:
   ```bash
   cd apps/prompt-game-web
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
   Navigate to http://localhost:3000

## Features

- **Interactive Lessons** - Structured scenarios with clear goals and answer formats
- **Real-time Scoring** - Get immediate feedback on your prompts with confidence scores
- **Turn-based Gameplay** - Limited turns encourage thoughtful prompting
- **Guardrail Detection** - Flags potential issues in your prompts
- **Reasoning Explanations** - Understand why your prompt scored the way it did

## Architecture

This app acts as a thin client that forwards requests to the `theory-engine-api` backend:

- **Frontend**: Next.js UI with lesson browser and game interface
- **API Routes**: 
  - `/api/lessons` - Fetches lesson list from puzzles.json
  - `/api/lessons/[id]` - Fetches individual lesson details
  - `/api/game/score` - Forwards prompt evaluation to theory-engine-api
- **Backend**: `theory-engine-api` handles prompt evaluation via `POST /api/theory/evaluate`

## Development

The app uses:
- **Next.js 16** - React framework
- **TypeScript** - Type safety
- **@dock108/ui** - Shared UI components (DockHeader, DockFooter)
- **@dock108/ui-kit** - Shared form components

## Lesson Data

Lessons are sourced from `swift-prototype/ios-app/AITrainerGame/AITrainerGame/Resources/puzzles.json`
to maintain consistency between web and iOS versions. The Swift prototype remains available
for reference and TestFlight distribution.
