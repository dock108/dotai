# UI Kit (React)

Shared component library for every dock108 React app.

## Goals
- Centralize typography, color tokens, spacing, and cards.
- Export ready-to-use components (TheoryCard, GuardrailBadge, Timeline, DataCallout).
- Publish via npm (workspace) for easy versioning.

## Setup plan
1. Bootstrap with Storybook + Tailwind preset.
2. Import components from `apps/playlist-web` as the first donors.
3. Add visual regression tests before wider usage.
