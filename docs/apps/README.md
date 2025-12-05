# Frontend Applications Documentation

This directory contains documentation for frontend applications in the dock108 monorepo.

## Active Applications

| App | Port | Description |
|-----|------|-------------|
| `theory-bets-web` | 3001 | Sports betting theory evaluation + admin UI |
| `theory-crypto-web` | 3002 | Crypto strategy interpreter |
| `theory-stocks-web` | 3003 | Stock analysis theory evaluation |
| `conspiracy-web` | 3004 | Conspiracy theory fact-checking |
| `highlights-web` | 3005 | Sports highlights playlist generator |
| `dock108-web` | 3000 | Unified landing portal |

## Documentation

- **[`prompt-game-ios.md`](prompt-game-ios.md)** - iOS Swift prototype documentation
- **[`prompt-game-ios-testing.md`](prompt-game-ios-testing.md)** - iOS testing guide
- **[`playlist-web-deprecated.md`](playlist-web-deprecated.md)** - Legacy playlist-web documentation (deprecated)

## Quick Start

See the main **[`../LOCAL_DEPLOY.md`](../LOCAL_DEPLOY.md)** for development setup.

Each app can be started individually:

```bash
cd apps/theory-bets-web
pnpm dev
```

## Shared Dependencies

All apps use shared packages:
- `@dock108/ui` - Common UI components (DockHeader, DockFooter)
- `@dock108/ui-kit` - Domain-specific components (TheoryForm, TheoryCard)
- `@dock108/js-core` - TypeScript SDK, React hooks, API client
