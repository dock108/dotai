# Data Privacy Model

## Core Principles

1. **No PII in Theory Text**: We never store personally identifiable information (PII) extracted from theory text. Only the raw theory text itself is stored.
2. **Anonymous User IDs**: User accounts use anonymous numeric IDs only. No email addresses, names, or other PII are stored in the database.
3. **Opt-in Model Improvement**: Users can explicitly opt-in to allow their anonymized data to be used for model improvement.

## Data Storage

### What We Store

#### Customer Accounts (`customer_accounts` table)
- `id`: Anonymous numeric ID (auto-increment)
- `tier`: Subscription tier (free/silver/gold/unlimited)
- `created_at`: Account creation timestamp
- `allow_model_improvement`: Boolean opt-in flag (default: `false`)

**No PII stored**: No email, name, phone number, or any identifying information.

#### Theories (`theories` table)
- `id`: Theory ID
- `domain`: Theory domain (bets/crypto/stocks/conspiracies/playlist)
- `user_id`: Optional anonymous user ID (nullable for anonymous submissions)
- `raw_text`: Original theory text as submitted
- `normalized_text`: Cleaned/normalized version (for guardrails processing)
- `created_at`: Submission timestamp

**No PII extraction**: We do not extract or store names, email addresses, phone numbers, or other PII from theory text.

#### Evaluations (`evaluations` table)
- Evaluation results linked to theories
- Verdict, confidence, reasoning
- Guardrail flags and model metadata

#### External Context Cache (`external_context_cache` table)
- Cached API responses (YouTube, odds, prices)
- Keyed by query hash, not user ID
- No user association

## Model Improvement Opt-in

Users can opt-in to allow their anonymized data to be used for model improvement:

- **Default**: `allow_model_improvement = false` (opt-out by default)
- **What it enables**: Aggregated statistics and pattern analysis
- **What it does NOT enable**: Individual theory text used for training without aggregation

### Aggregated Analytics Only

When `allow_model_improvement = true`, we may use data for:

- **Aggregated statistics**: "X% of BTC theories mentioning 'alt liquidity' performed worse than random"
- **Pattern analysis**: Domain-specific pattern frequency analysis
- **Model calibration**: Confidence score calibration based on historical outcomes

**We never**:
- Use individual theory text for training without aggregation
- Share individual theories with third parties
- Link theories to identifiable users

## Future Enhancements

### Embeddings-Only Storage

In the future, we may transition to storing only normalized embeddings instead of raw text:

- `raw_text` → Embedding vector (via sentence transformers)
- Original text discarded after embedding generation
- Enables semantic search and similarity matching without storing full text

This would further reduce privacy risk while maintaining functionality.

### Data Retention

- **Active theories**: Stored indefinitely (or until user deletion request)
- **Cached context**: TTL-based expiration (see caching rules in `ARCHITECTURE.md`)
- **Evaluation results**: Linked to theories, follow same retention policy

## User Rights

Users can:

1. **Request data deletion**: All theories and evaluations linked to their anonymous user ID will be deleted
2. **Opt-out of model improvement**: Set `allow_model_improvement = false` at any time
3. **Submit anonymously**: Theories can be submitted without a user account (`user_id = null`)

## Compliance

This privacy model is designed to:

- Minimize data collection (no PII)
- Provide user control (opt-in for model improvement)
- Enable transparency (clear documentation of what is stored)
- Support future enhancements (embeddings-only storage path)

## Implementation Notes

- All database models include privacy comments
- Guardrails layer does not extract PII from input
- Analytics queries use aggregated statistics only
- No third-party analytics services that collect PII

