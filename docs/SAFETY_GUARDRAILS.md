# Safety & Guardrails

The guardrail layer sits between every dock108 surface and any LLM (OpenAI or custom). It enforces compliance, filters abuse, and maintains consistent prompt formats.

## 1. Objectives

1. Block disallowed content before model calls.
2. Enforce per-domain policies (sports betting compliance, financial disclaimers, conspiracy sensitivity).
3. Normalize prompts so the LLM always receives structured context, not raw user text.
4. Validate responses, redact sensitive data, and log lineage for future audits.

## 2. Pipeline

```
Submission → Input validation → Content policy scan → Domain policy hooks
          → Prompt builder w/ templating + contextual data
          → LLM provider (OpenAI today) → Response validator (JSON schema)
          → Output filters (privacy, redaction) → Persistent storage + analytics
```

## 3. Enforcement Techniques

- **Content filters**: OpenAI moderation API + custom keyword/regex lists.
- **Statistical checks**: heuristics for hallucination risk (e.g., high confidence with zero data sources triggers downgrade).
- **Reference validation**: ensure every claim references fetched data or is labeled as speculation.
- **Human-in-the-loop**: flagged responses route to `manual_review` queue (future admin UI).

## 4. Prompt Templates

- Shared `System` prompt describing the domain, available data, and output schema.
- `User` block is structured: `theory`, `supporting_data`, `risk_profile`, `desired_format`.
- Templates live in `packages/py-core/guardrails/` so both FastAPI and workers reuse them.

## 5. Logging + Auditing

- Every guardrail decision records: timestamp, user anon id, domain, rule triggered, outcome.
- Store logs in Postgres + ship to Loki/Grafana for search.
- Weekly review of false positives/negatives to tune rules.

## 6. Future Upgrades

- Train a small classifier to pre-label conspiratorial vs. legitimate theories.
- Add `prompt caching` for repeated safe inputs.
- Integrate Attribution Reporting (ARA) style data to show exactly which inputs influenced the card output.
