# Documentation Index

This directory contains all documentation for the dock108 monorepo.

## Quick Start

**New to the project?** Start here:
- **[`LOCAL_DEPLOY.md`](LOCAL_DEPLOY.md)** - Comprehensive local development and testing guide (Sports Highlight Channel feature)
- **[`../README.md`](../README.md)** - Main project README with overview and setup instructions

## Documentation by Category

### 🚀 Getting Started & User Guides

- **[`LOCAL_DEPLOY.md`](LOCAL_DEPLOY.md)** - Complete local development setup guide (includes quick start section)
- **[`HIGHLIGHTS_USER_GUIDE.md`](HIGHLIGHTS_USER_GUIDE.md)** - End-user guide for the Sports Highlight Channel feature

### 📡 API Documentation

- **[`HIGHLIGHTS_API.md`](HIGHLIGHTS_API.md)** - Complete API documentation for highlight endpoints
- **[`THEORY_ENGINE.md`](THEORY_ENGINE.md)** - Theory engine API blueprint and design

### 🏗️ Architecture & System Design

- **[`ARCHITECTURE.md`](ARCHITECTURE.md)** - Overall system architecture and monorepo structure
- **[`THEORY_SURFACES.md`](THEORY_SURFACES.md)** - Theory surfaces design and implementation
- **[`SAFETY_GUARDRAILS.md`](SAFETY_GUARDRAILS.md)** - Guardrail system documentation
- **[`DATA_PRIVACY.md`](DATA_PRIVACY.md)** - Privacy model and data handling policies

### ⚙️ Feature Documentation

#### Theory Evaluation Surfaces

- **[`THEORY_SURFACES.md`](THEORY_SURFACES.md)** - Theory surfaces design and implementation
- **[`THEORY_ENGINE.md`](THEORY_ENGINE.md)** - Theory engine API blueprint and design
- **[`CONSPIRACY_THEORY.md`](CONSPIRACY_THEORY.md)** - Narrative-driven conspiracy analysis, rubric-based scoring, and data sources
- **[`SAFETY_GUARDRAILS.md`](SAFETY_GUARDRAILS.md)** - Guardrail system for content filtering and safety

#### Sports Features

- **[`HIGHLIGHT_PARSING.md`](HIGHLIGHT_PARSING.md)** - AI parsing system for highlight requests
- **[`SPORTS_SEARCH.md`](SPORTS_SEARCH.md)** - Sports-focused YouTube search implementation
- **[`PLAYLIST_DATABASE.md`](PLAYLIST_DATABASE.md)** - Database schema and caching design
- **[`highlight-mvp.md`](highlight-mvp.md)** - Current constraints, limitations, and future ideas
- **[`YOUTUBE_SETUP.md`](YOUTUBE_SETUP.md)** - YouTube OAuth setup and token management guide
- **[`../LOAD_SPORTS_DATA.md`](../LOAD_SPORTS_DATA.md)** - Guide for loading sports data via admin UI

### 📋 Planning & Reference

- **[`ROADMAP.md`](ROADMAP.md)** - Future roadmap and planned features

### 📦 Archived Documents

Historical reference documents are in the [`archive/`](archive/) folder:
- `archive/PLAYLIST_MVP.md` - Original playlist-web MVP (legacy)
- `archive/highlight-phase-notes.md` - Historical audit notes (completed work)
- `archive/EXISTING_APPS.md` - Phase 0 planning doc (outdated)
- `archive/HIGHLIGHT_FLOW.md` - Planning doc with gaps that have been addressed

## Documentation Status

✅ **Up to Date**:
- `LOCAL_DEPLOY.md` - Comprehensive local deployment guide
- `ARCHITECTURE.md` - System architecture and monorepo structure
- `HIGHLIGHTS_API.md` - Complete API documentation with metrics and watch token endpoints
- `HIGHLIGHT_PARSING.md` - AI parsing system documentation
- `SPORTS_SEARCH.md` - Search module documentation
- `PLAYLIST_DATABASE.md` - Database schema documentation
- `highlight-mvp.md` - Current constraints and limitations
- `CONSPIRACY_THEORY.md` - Narrative-driven conspiracy analysis documentation
- `THEORY_SURFACES.md` - Theory surfaces design and implementation
- `THEORY_ENGINE.md` - Theory engine blueprint
- `API_KEYS_SETUP.md` - API key setup guide for all services
- `SAFETY_GUARDRAILS.md` - Guardrail system documentation
- `DATA_PRIVACY.md` - Privacy model and data handling
- `ROADMAP.md` - Future roadmap and planned features
- `YOUTUBE_SETUP.md` - OAuth setup and token management guide
- `../LOAD_SPORTS_DATA.md` - Sports data loading guide

📝 **Planning Documents** (archived):
- See `archive/` folder for historical planning documents

## Contributing to Documentation

When updating documentation:

1. **Update the relevant doc file** with accurate, tested information
2. **Update this index** if adding, removing, or reorganizing docs
3. **Test code examples** to ensure they work
4. **Use clear headings** and structure for easy navigation
5. **Link between related docs** for better discoverability

## Documentation Standards

- **Code examples** should be tested and working
- **API documentation** should include request/response examples
- **Guides** should be step-by-step and reproducible
- **Architecture docs** should include diagrams where helpful
- **Keep docs current** - remove outdated information or mark as deprecated
