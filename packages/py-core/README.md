# Py Core

Python package that stores shared schemas, guardrail helpers, and scoring utilities.

## Planned modules
- `schemas/theory.py` – TheorySubmission, TheoryCard, GuardrailVerdict
- `prompting/templates.py` – canonical prompt builders
- `scoring/metrics.py` – grading heuristics, Monte Carlo sims
- `clients/llm.py` – unified interface for OpenAI + custom models

First consumer will be `services/theory-engine-api`, followed by `services/data-workers`.
