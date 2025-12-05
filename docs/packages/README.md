# Shared Packages Documentation

This directory contains documentation for shared packages in the dock108 monorepo.

## Packages

| Package | Language | Description |
|---------|----------|-------------|
| `py-core` | Python | Schemas, guardrails, scoring utilities |
| `js-core` | TypeScript | API client, React hooks, type definitions |
| `ui` | React | Shared UI components (DockHeader, DockFooter, theme) |
| `ui-kit` | React | Domain-specific components (TheoryForm, TheoryCard) |

## Documentation

- **[`py-core.md`](py-core.md)** - Python core package documentation

## Package Structure

```
packages/
├── py-core/           # Python shared library
│   ├── py_core/
│   │   ├── schemas/   # Pydantic models
│   │   ├── guardrails/# Safety guardrails
│   │   └── utils/     # Shared utilities
│   └── pyproject.toml
│
├── js-core/           # TypeScript SDK
│   ├── src/
│   │   ├── api/       # API client
│   │   ├── hooks/     # React hooks
│   │   └── types/     # TypeScript types
│   └── package.json
│
├── ui/                # Shared UI components
│   └── src/
│       └── components/
│
└── ui-kit/            # Domain-specific UI
    └── src/
        └── components/
```

## Usage

### Python (py-core)

```python
from py_core.schemas import TheoryRequest, TheoryResponse
from py_core.guardrails import evaluate_guardrails
```

### TypeScript (js-core)

```typescript
import { useTheoryEvaluation } from "@dock108/js-core";
import { TheoryForm, TheoryCard } from "@dock108/ui-kit";
```
