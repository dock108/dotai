# Conspiracy Theory Evaluation

## Overview

The conspiracy theory evaluation feature analyzes user-submitted conspiracy theories using Wikipedia and fact-check databases to provide evidence-based assessments. The system extracts evidence for and against claims, identifies historical parallels, and calculates likelihood ratings.

## Data Sources

### Wikipedia API

- **Endpoint**: `https://en.wikipedia.org/api/rest_v1/`
- **Authentication**: None required (public API)
- **Rate Limits**: No official limits, but be respectful (recommended: < 200 requests/second)
- **Caching**: Results cached for 30 days
- **What it provides**: Article summaries, key facts, URLs

### Google Fact Check Explorer API

- **Endpoint**: `https://factchecktools.googleapis.com/v1alpha1/claims:search`
- **Authentication**: API key required (optional)
- **Rate Limits**: Free tier available, see [Google Cloud Console](https://console.cloud.google.com/)
- **Caching**: Results cached for 30 days
- **What it provides**: Fact-check ratings, publisher information, review URLs
- **Setup**: See [Local Deployment Guide](LOCAL_DEPLOY.md#3-get-google-fact-check-api-key-optional---for-conspiracy-theory-evaluation)

## API Key Setup

### Google Fact Check API Key (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Fact Check Tools API"
4. Create credentials (API Key)
5. Copy the API key
6. Add to `.env` file:
   ```bash
   GOOGLE_FACTCHECK_API_KEY=your-google-factcheck-api-key-here
   ```

**Note**: The system works without this API key, but fact-check results will be limited. Wikipedia results will still be available.

## How It Works

### 1. Context Fetching

When a conspiracy theory is submitted:

1. **Wikipedia Search**: Searches for relevant Wikipedia articles matching the query
2. **Fact-Check Search**: Queries Google Fact Check API for related claims (if API key configured)
3. **Caching**: Results are cached for 30 days to reduce API calls

### 2. Analysis

The system analyzes the fetched context to:

- **Generate Narrative**: Calls the Conspiracy Narrative Engine prompt (OpenAI) with user text + Wikipedia/fact-check context.
- **Tell the Story**: Produces a 4–7 paragraph mini documentary covering origins, main figures, cultural beats, and turning points.
- **Claims vs Evidence**: Lists each major talking point and the strongest counter-evidence available.
- **Compute Confidence**: Applies a weighted rubric:
  - Historical documentation (30%)
  - Independent corroboration (20%)
  - Scientific plausibility (20%)
  - Expert consensus (20%)
  - Internal coherence (10%)
- **Surface Sources & Fuel**: Returns a readable source list plus modern drivers keeping the theory alive.

### 3. Response Structure

The API returns:

```json
{
  "claim_text": "The moon landing hoax theory claims NASA staged the Apollo 11 broadcast in 1969.",
  "story_sections": ["Paragraph 1", "Paragraph 2", "..."],
  "claims_vs_evidence": [
    { "claim": "Shadows diverge on the lunar surface", "evidence": "Uneven terrain naturally bends shadows", "verdict": "debunked" }
  ],
  "confidence_score": 7,
  "verdict_text": "Very Low Confidence (7/100) — extensive photographic, physical, and testimonial records contradict the hoax narrative.",
  "sources_used": ["NASA mission logs", "Apollo photo forensics", "BBC Science documentary"],
  "fuels_today": ["Viral YouTube explainers", "Cold War-era mistrust"]
}
```

## Caching Strategy

- **Cache Duration**: 30 days for conspiracy context
- **Cache Key**: Based on query text and source types
- **Cache Invalidation**: Automatic expiration after 30 days
- **Cache Storage**: In-memory (can be upgraded to Redis in production)

## Rate Limits and Best Practices

### Wikipedia API

- No official rate limits, but be respectful
- Recommended: < 200 requests/second
- Caching helps reduce API calls significantly

### Google Fact Check API

- Free tier available
- Check [Google Cloud Console](https://console.cloud.google.com/) for your specific limits
- Caching helps reduce API calls

## Error Handling

The system gracefully handles:

- **Missing API Keys**: Returns empty fact-check results with limitation message
- **Network Failures**: Returns partial results (Wikipedia if fact-check fails, or vice versa)
- **API Errors**: Logs errors and continues with available data
- **Empty Results**: Provides helpful limitation messages

## Limitations

1. **Wikipedia Coverage**: Not all conspiracy theories have Wikipedia articles
2. **Fact-Check Availability**: Fact-check databases may not cover all claims
3. **Recent Events**: Fact-check databases may not have recent claims (< 90 days)
4. **Classified Information**: Some claims involve classified documents that aren't publicly available
5. **Fringe Sources**: System only uses mainstream sources (Wikipedia, verified fact-checkers)

## Example Queries

- "JFK second shooter theory"
- "Moon landing hoax claims"
- "9/11 inside job theory"

## Testing

To test the implementation:

1. Start the backend server (see [Local Deployment Guide](LOCAL_DEPLOY.md))
2. Start the frontend (`apps/theory-conspiracy-web`) and enter a conspiracy theory
3. Verify:
   - Claim sentence rewrites the user text cleanly
   - Story section renders 4–7 narrative paragraphs
   - Claims vs evidence bullets align with the prompt structure
   - Confidence badge shows 0–100 score w/ weight breakdown (check API JSON)
   - Sources consulted and “What fuels this theory today?” are populated when data is available

## Troubleshooting

### No Wikipedia Results

- Check if the query matches a known Wikipedia article title
- Try rephrasing the query
- Some topics may not have Wikipedia coverage

### No Fact-Check Results

- Verify `GOOGLE_FACTCHECK_API_KEY` is set in `.env`
- Check API key is valid in Google Cloud Console
- Some claims may not have fact-check coverage
- Recent claims (< 90 days) may not be in databases yet

### Low Likelihood Ratings

- This is expected for most conspiracy theories
- Ratings are based on available evidence from mainstream sources
- Low ratings don't mean the system is broken - they reflect limited supporting evidence


