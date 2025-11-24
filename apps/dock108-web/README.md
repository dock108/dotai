# Dock108 Web Hub

Next.js landing portal that links every Dock108 surface (game, highlights, bets, stocks, crypto, conspiracy). Uses the shared `@dock108/ui` package for typography, tiles, and header/footer components.

## Quick Start

1. **Install dependencies** (from repo root):
   ```bash
   pnpm install
   ```

2. **Start the development server**:
   ```bash
   cd apps/dock108-web
   pnpm dev
   ```

3. **Open your browser**:
   Navigate to http://localhost:3000

## Scripts

```bash
pnpm dev      # Start development server on port 3000
pnpm build    # Build for production
pnpm start    # Start production server
pnpm lint     # Run ESLint
```

## Development

The app uses:
- **Next.js 16** - React framework
- **TypeScript** - Type safety
- **@dock108/ui** - Shared UI components (AppTile, DockHeader, DockFooter)

## Notes

- Imports `@dock108/ui/theme.css` in `layout.tsx` to stay on-brand
- `page.tsx` defines the tile metadata—keep hrefs in sync with Traefik routing in `infra/docker-compose.yml`
- No backend API required—this is a static landing page with links to other apps
