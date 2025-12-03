# Theory Surfaces

This document describes the domain-specific theory evaluation surfaces in the dock108 monorepo.

## Overview

The theory surfaces are Next.js applications that allow users to evaluate theories in specific domains:
- **bets.dock108.ai** - Betting theories with edge estimates and Kelly sizing
- **crypto.dock108.ai** - Cryptocurrency pattern analysis
- **stocks.dock108.ai** - Stock market fundamentals and correlation analysis
- **conspiracies.dock108.ai** - Conspiracy theory fact-checking with evidence analysis

All surfaces share:
- Common UI components from `@dock108/ui-kit`
- Type-safe API client from `@dock108/js-core`
- Consistent error handling and loading states
- Domain-specific response fields displayed in collapsible sections

## Architecture

### Frontend Apps

Each theory surface is a Next.js app in `apps/theory-{domain}-web/`:

```
apps/
  theory-bets-web/      # Port 3001
  theory-crypto-web/    # Port 3002
  theory-stocks-web/    # Port 3003
  theory-conspiracy-web/ # Port 3004
```

### Shared Packages

#### `@dock108/js-core`

TypeScript SDK providing:
- **APIClient**: Base HTTP client with retry logic and error handling
- **TheoryAPI**: Type-safe methods for each domain endpoint
- **React Hooks**: `useTheoryEvaluation`, `useBetsEvaluation`, `useCryptoEvaluation`, etc.
- **Types**: TypeScript types matching backend Pydantic schemas

#### `@dock108/ui-kit`

Shared React components:
- **TheoryForm**: Input form with examples and domain-specific fields
- **TheoryCard**: Response display with domain-specific sections
- **LoadingSpinner**: Loading state indicator
- **ErrorDisplay**: Error message display with retry
- **DomainHeader**: Consistent header with title/subtitle
- **Container, Section, PageLayout**: Layout components

### Backend API

All surfaces use the same `services/theory-engine-api` backend:

- `POST /api/theory/bets` - Evaluate betting theory
- `POST /api/theory/crypto` - Evaluate crypto theory
- `POST /api/theory/stocks` - Evaluate stock theory
- `POST /api/theory/conspiracies` - Evaluate conspiracy theory

See `services/theory-engine-api/app/routers/` for implementation details.

## Domain-Specific Features

### Bets (`theory-bets-web`)

**Request Fields:**
- `text`: Theory text (required)
- `sport`: Sport name (e.g., "NBA", "NFL") (optional)
- `league`: League name (optional)
- `horizon`: "single_game" or "full_season" (default: "single_game")

**Response Fields:**
- `likelihood_grade`: A-F grade for likelihood
- `edge_estimate`: Estimated edge (0-1)
- `kelly_sizing_example`: Long-term outcome with Kelly-lite sizing

**Examples:**
- "The Lakers will cover the spread because their defense improved after the trade deadline"
- "MLB moneyline trend: Teams with 3+ consecutive wins have 65% win rate"

### Crypto (`theory-crypto-web`)

**Request Fields:**
- `text`: Theory text (required)
- `domain`: "crypto" (optional, auto-detected)

**Response Fields:**
- `pattern_frequency`: How often pattern held historically (0-1)
- `failure_periods`: List of periods where pattern failed
- `remaining_edge`: Realistic edge remaining today (if any)

**Examples:**
- "Bitcoin dominance dropping means alt season is coming"
- "ETH/BTC ratio breaking out signals rotation into alts"

### Stocks (`theory-stocks-web`)

**Request Fields:**
- `text`: Theory text (required)
- `domain`: "stocks" (optional, auto-detected)

**Response Fields:**
- `correlation_grade`: Grade for narrative vs historical correlations
- `fundamentals_match`: Whether fundamentals support the theory
- `volume_analysis`: Volume pattern analysis

**Examples:**
- "AAPL will outperform because their services revenue is growing faster than hardware"
- "Tech stocks with high R&D spend outperform during innovation cycles"

### Conspiracies (`theory-conspiracy-web`)

**Request Fields:**
- `text`: Theory text (required)
- `domain`: "conspiracies" (optional, auto-detected)

**Response Fields:**
- `likelihood_rating`: Likelihood rating 0-100
- `evidence_for`: List of evidence supporting the claim
- `evidence_against`: List of evidence against the claim
- `historical_parallels`: Similar claims that were true/false
- `missing_data`: Where data is missing

**Examples:**
- "JFK second shooter theory"
- "Moon landing hoax claims"

**Note**: Conspiracies surface has guardrails to prevent evaluation of recent events (within last 90 days).

## Development

### Local Setup

1. **Install dependencies** (from monorepo root):
   ```bash
   pnpm install
   ```

2. **Start backend** (if not already running):
   ```bash
   cd services/theory-engine-api
   uv sync
   uv pip install -e ../../packages/py-core
   uv run uvicorn app.main:app --reload
   ```

3. **Start frontend** (choose one):
   ```bash
   # Bets
   cd apps/theory-bets-web
   pnpm dev  # Runs on port 3001

   # Crypto
   cd apps/theory-crypto-web
   pnpm dev  # Runs on port 3002

   # Stocks
   cd apps/theory-stocks-web
   pnpm dev  # Runs on port 3003

   # Conspiracies
   cd apps/theory-conspiracy-web
   pnpm dev  # Runs on port 3004
   ```

4. **Set environment variables**:
   Create `.env.local` in each app directory:
   ```bash
   NEXT_PUBLIC_THEORY_ENGINE_URL=http://localhost:8000
   ```

### Testing

Each surface can be tested independently:

1. Open the app in browser (e.g., `http://localhost:3001` for bets)
2. Enter a theory in the text area
3. Click "Evaluate Theory"
4. Review the response card with domain-specific fields

### Common Patterns

All surfaces follow the same pattern:

```tsx
import { useBetsEvaluation } from "@dock108/js-core";
import { TheoryForm, TheoryCard, ErrorDisplay, LoadingSpinner } from "@dock108/ui-kit";

export default function Home() {
  const { data, loading, error, evaluate } = useBetsEvaluation();

  const handleSubmit = async (text: string) => {
    await evaluate({ text, domain: "bets" });
  };

  return (
    <Container>
      <DomainHeader title="bets.dock108.ai" subtitle="..." />
      <Section>
        <TheoryForm domain="bets" onSubmit={handleSubmit} loading={loading} />
      </Section>
      {loading && <LoadingSpinner />}
      {error && <ErrorDisplay error={error} />}
      {data && <TheoryCard response={data} domain="bets" />}
    </Container>
  );
}
```

## Deployment

All theory surfaces are included in the Docker Compose setup (`infra/docker-compose.yml`) and can be deployed together with the backend API.

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for production deployment instructions.

## Future Enhancements

- [ ] User authentication and theory history
- [ ] Save favorite theories
- [ ] Share theory evaluations
- [ ] Advanced filtering and search
- [ ] Real-time updates for market-based theories
- [ ] Integration with data workers for pre-fetched context

