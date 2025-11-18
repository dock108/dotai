# Theory Engine (FastAPI) Blueprint

## 1. Responsibilities

1. Accept theory submissions from any frontend (bets, crypto, stocks, conspiracies, playlists, AI game insights).
2. Enrich and classify the submission (detect domains, extract entities, estimate risk, flag NSFW/abuse).
3. Load + join relevant structured data (YouTube catalog cache, betting lines, OHLCV prices, macro feeds).
4. Build a guardrailed prompt, call the selected LLM, and translate the response into a "Card" schema.
5. Persist inputs/outputs, anonymized theory text, data lineage, and guardrail verdicts.

## 2. Service Layout

```
services/theory-engine-api/
  app/
    main.py             # FastAPI app + routers
    dependencies.py     # DB/Redis clients
    routers/
      playlists.py
      bets.py
      crypto.py
      stocks.py
      conspiracies.py
    models/
      theory.py         # Pydantic models shared via py-core
      card.py
      guardrails.py
    llm/
      prompt_builder.py
      providers.py      # OpenAI + future model registry
      guardrails.py     # Safety filters + evaluator hooks
    data/
      youtube_cache.py
      odds_service.py
      market_data.py
```

## 3. Shared Schema (py-core)

- `TheorySubmission` – text, domain hints, metadata (risk tolerance, anonymity, language, privacy toggle).
- `TheoryCard` – canonical response with sections: `inputs`, `analysis`, `data_gaps`, `likelihood`, `next_steps`, `simulation`.
- `GuardrailVerdict` – per-request outcomes (allowed, require_human_review, blocked) + reasons.

These live in `packages/py-core` so both FastAPI and workers reuse them.

## 4. Guardrail Flow

1. **Syntactic filters** – prompt length, profanity/NSFW, sensitive keywords.
2. **Domain policy** – e.g., conspiracies vs. disallowed topics, sports betting compliance.
3. **Template enforcement** – ensure the LLM receives structured JSON instructions, not free-form user text.
4. **Response validation** – parse JSON, validate against `TheoryCard` schema, re-ask or downgrade model if invalid.

## 5. Data Integrations

| Domain      | Data Worker Source                | Refresh Cadence |
|-------------|------------------------------------|-----------------|
| Bets        | Odds API / Sportradar snapshot      | 30s – 5m        |
| Crypto      | CCXT / exchange websockets          | 15s             |
| Stocks      | Polygon.io / Tiingo end-of-day      | 1m – 15m        |
| Conspiracy  | News API + custom curated dataset   | hourly          |
| Playlist    | YouTube Data API + cached metadata  | on-demand + 1h  |

Workers push normalized payloads into Redis/Postgres. The API reads from there before LLM usage so 3rd-party hits stay within quotas.

## 6. Interfaces

- REST/JSON with typed endpoints: `POST /v1/theories/{domain}` and `POST /v1/theories/multi`.
- Webhooks for long-running analyses (future) using `job_id` + polling.
- Admin endpoints for guardrail overrides and manual reviews.

## 7. Observability

- Structured logging (Logfire or OpenTelemetry) with request_id + guardrail decisions.
- Metrics: per-domain throughput, guardrail block rate, LLM latency, cache hit rate.
- Traces span guardrail → data loaders → LLM provider.

## 8. Migration Plan

1. Stub FastAPI app with playlist endpoints that proxy to the existing Next.js API route.
2. Gradually move playlist logic into `py-core`/`theory-engine-api` while keeping UI unchanged.
3. Add bet/crypto/stocks routers once their data workers exist.
4. Expose a GraphQL/REST hybrid (optional) once multiple clients need richer querying.
