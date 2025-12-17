# Documentation Index

This directory contains all documentation for the dock108 monorepo.

## Quick Start

**New to the project?** Start here:
- **[`../README.md`](../README.md)** - Main project README with overview
- **[`START.md`](START.md)** - Quick Docker-based startup guide
- **[`LOCAL_DEPLOY.md`](LOCAL_DEPLOY.md)** - Comprehensive local development guide

## Documentation by Category

### 🚀 Getting Started

| Document | Description |
|----------|-------------|
| [`START.md`](START.md) | Quick Docker-based startup |
| [`LOCAL_DEPLOY.md`](LOCAL_DEPLOY.md) | Complete local development setup |
| [`API_KEYS_SETUP.md`](API_KEYS_SETUP.md) | API key setup for all services |
| [`YOUTUBE_SETUP.md`](YOUTUBE_SETUP.md) | YouTube OAuth setup |

### 📡 API Documentation

| Document | Description |
|----------|-------------|
| [`HIGHLIGHTS_API.md`](HIGHLIGHTS_API.md) | Highlights endpoint documentation |
| [`THEORY_ENGINE.md`](THEORY_ENGINE.md) | Theory engine API blueprint |

### 🏗️ Architecture

| Document | Description |
|----------|-------------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture overview |
| [`THEORY_SURFACES.md`](THEORY_SURFACES.md) | Theory surfaces design |
| [`UNIFIED_THEORY_BETS.md`](UNIFIED_THEORY_BETS.md) | v1 theory bets pipeline |
| [`SAFETY_GUARDRAILS.md`](SAFETY_GUARDRAILS.md) | Guardrail system |
| [`DATA_PRIVACY.md`](DATA_PRIVACY.md) | Privacy and data handling |

### ⚙️ Features

#### Theory Evaluation
- [`THEORY_SURFACES.md`](THEORY_SURFACES.md) - Theory surfaces implementation
- [`UNIFIED_THEORY_BETS.md`](UNIFIED_THEORY_BETS.md) - v1 bets pipeline
- [`CONSPIRACY_THEORY.md`](CONSPIRACY_THEORY.md) - Conspiracy analysis engine

#### Theory Builder (Admin EDA)
- [`eda-current-state.md`](eda-current-state.md) - Theory Builder architecture and flow
- [`FEATURE_LAYERS.md`](FEATURE_LAYERS.md) - Feature categories and presets

#### Sports Features
- [`HIGHLIGHT_PARSING.md`](HIGHLIGHT_PARSING.md) - AI parsing for highlight requests
- [`SPORTS_SEARCH.md`](SPORTS_SEARCH.md) - YouTube search implementation
- [`PLAYLIST_DATABASE.md`](PLAYLIST_DATABASE.md) - Database schema and caching
- [`HIGHLIGHTS_MVP.md`](HIGHLIGHTS_MVP.md) - Current constraints and limitations
- [`HIGHLIGHTS_USER_GUIDE.md`](HIGHLIGHTS_USER_GUIDE.md) - End-user guide
- [`LOAD_SPORTS_DATA.md`](LOAD_SPORTS_DATA.md) - Sports data ingestion guide

#### Admin & Utilities
- [`ADMIN_UTILITIES_TEMPLATE.md`](ADMIN_UTILITIES_TEMPLATE.md) - Admin utilities pattern
- [`UI_GUIDE.md`](UI_GUIDE.md) - UI system guide

### 🏭 Deployment & Infrastructure

| Document | Description |
|----------|-------------|
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Production deployment guide |
| [`infra/README.md`](infra/README.md) | Infrastructure overview |
| [`infra/docker.md`](infra/docker.md) | Docker configuration |
| [`infra/k8s.md`](infra/k8s.md) | Kubernetes (planned) |

### 📦 Components

| Directory | Description |
|-----------|-------------|
| [`apps/README.md`](apps/README.md) | Frontend applications |
| [`services/README.md`](services/README.md) | Backend services |
| [`packages/README.md`](packages/README.md) | Shared libraries |

### 📋 Planning

| Document | Description |
|----------|-------------|
| [`ROADMAP.md`](ROADMAP.md) | Project roadmap |

### 📦 Archive

Historical documents in [`archive/`](archive/):
- `PLAYLIST_MVP.md` - Original playlist-web MVP
- `highlight-phase-notes.md` - Historical audit notes
- `EXISTING_APPS.md` - Phase 0 planning doc
- `HIGHLIGHT_FLOW.md` - Early planning doc

## Contributing

When updating documentation:
1. Update the relevant doc file
2. Update this index if adding/removing docs
3. Test code examples
4. Keep docs current - remove outdated info
