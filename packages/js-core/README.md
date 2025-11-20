# JS Core

TypeScript utilities and SDK shared across the React apps.

## Contents

- **API SDK**: REST client with error handling, retry logic, and type-safe endpoints
- **TypeScript Types**: Types matching py-core Pydantic schemas
- **React Hooks**: `useTheoryEvaluation` and domain-specific hooks for theory evaluation

## Usage

### Basic API Client

```typescript
import { createClient, TheoryAPI } from "@dock108/js-core";

const client = createClient(); // Uses NEXT_PUBLIC_THEORY_ENGINE_URL or localhost:8000
const api = new TheoryAPI(client);

// Evaluate a theory
const response = await api.evaluateBets({
  text: "The Lakers will cover the spread",
  sport: "NBA",
});
```

### React Hooks

```typescript
import { useBetsEvaluation } from "@dock108/js-core";

function MyComponent() {
  const { data, loading, error, evaluate } = useBetsEvaluation();

  const handleSubmit = async () => {
    await evaluate({
      text: "The Lakers will cover the spread",
      sport: "NBA",
    });
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (data) return <div>{data.summary}</div>;
  return <button onClick={handleSubmit}>Evaluate</button>;
}
```

### Highlights API

```typescript
import { createClient, HighlightsAPI } from "@dock108/js-core";

const client = createClient();
const highlights = new HighlightsAPI(client);

const playlist = await highlights.planPlaylist({
  query_text: "NFL Week 12 highlights, 1 hour",
  mode: "sports_highlight",
});
```

## Types

All types are exported and match the backend Pydantic schemas:
- `TheoryRequest`, `TheoryResponse`
- `BetsRequest`, `BetsResponse`
- `CryptoResponse`, `StocksResponse`, `ConspiraciesResponse`
- `Domain`, `DataSource`
- `APIError`, `NetworkError`
