# UI Guide – Light Theme and Admin Patterns

## Tokens and theme

- All theory apps use a light theme with dark text.
- Core variables:
  - `--dock-bg`, `--dock-surface`, `--dock-elevated`, `--dock-border`
  - `--dock-text`, `--dock-text-muted`
  - `--dock-accent`, `--dock-accent-secondary`
- For crypto/stocks apps, use the semantic tokens from `src/styles/tokens.css`:
  - `--background`, `--foreground`, `--card`, `--border`, `--primary`, etc.

## Admin components

- Shared admin primitives live in `apps/theory-bets-web/src/components/admin`:
  - `AdminCard` – standard panel/card shell with optional header.
  - `AdminStatCard` – compact stat tiles for dashboard numbers.
  - `AdminTable` – basic table with light header and row hover.
  - `StatusBadge`, `LoadingState`, `ErrorState`, `AdminNav`.
- New admin pages should:
  - Use `AdminStatCard` for top-line stats.
  - Wrap sections in `AdminCard`.
  - Use `AdminTable` for tabular data where possible.

## Copy and emojis

- Keep copy clear and neutral; avoid emojis in:
  - Nav labels
  - Primary headings and section titles
  - Textareas, placeholders, and helper text
- Arrows and flows should use simple words like “to”, not arrow glyphs.


