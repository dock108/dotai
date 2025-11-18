# Sports Highlight Phase - Code Audit & Cleanup Notes

**Phase**: Sports Highlight Channel MVP  
**Date**: 2024-11-18  
**Status**: Step 0 - Repo Review & Cleanup

## Executive Summary

This document catalogs the existing playlist/YouTube codebase to identify:
- What stays as "core" functionality
- What gets deprecated/removed
- What needs refactoring into shared packages

## 1. Current State Analysis

### 1.1 Apps Structure

#### `apps/playlist-web/` (Active)
**Status**: ✅ Keep - Active Next.js app, will be refactored

**Key Components**:
- `src/lib/youtube.ts` - YouTube Data API client (search + video details)
- `src/lib/youtubePlaylist.ts` - Playlist creation via OAuth
- `src/lib/topicParser.ts` - LLM-based topic parsing
- `src/lib/videoFiltering.ts` - Video scoring and filtering
- `src/lib/videoClassifier.ts` - Video tag classification (intro/context/deep_dive/ending)
- `src/lib/playlistBuilder.ts` - Playlist sequencing logic
- `src/lib/playlistService.ts` - Orchestration layer
- `src/lib/topicRAG.ts` - RAG-enhanced topic understanding
- `src/lib/queryOptimizer.ts` - AI-optimized search query generation
- `src/lib/semanticMatcher.ts` - Semantic video matching
- `src/lib/videoAnalyzer.ts` - Video analysis utilities
- `src/lib/progress.ts` - Progress tracking for UI
- `src/lib/debugLogger.ts` - Debug logging (development only)
- `src/app/api/playlist/route.ts` - Main API endpoint
- `src/app/api/debug/route.ts` - Debug endpoint (⚠️ REMOVE)

**Frontend**:
- `src/app/page.tsx` - Main UI (uses TheoryForm from ui-kit)
- `src/app/page.module.css` - Styling

**Scripts**:
- `scripts/get-youtube-token.js` - OAuth token helper (✅ Keep)

#### `apps/playlist-web/legacy-mvp/` (Reference)
**Status**: 📦 Archive - Keep for reference, mark as deprecated

**Purpose**: Earliest prototype, kept for reference per README  
**Action**: Add deprecation notice, move to `docs/archive/` or keep with clear marking

### 1.2 Services Structure

#### `services/theory-engine-api/app/routers/playlist.py`
**Status**: ✅ Keep - Backend API endpoint

**Current Implementation**:
- Uses `fetch_youtube_context()` from `py_core.data.fetchers`
- Placeholder video data generation
- Basic scoring and classification
- **Gap**: Not using real YouTube API yet (returns mock data)

**Action**: Extend to support sports highlight mode

### 1.3 Packages Structure

#### `packages/py-core/py_core/data/fetchers.py`
**Status**: ✅ Keep - Shared data fetching

**Current**:
- `fetch_youtube_context()` - Placeholder implementation
- Caching layer via `ContextCache`
- **Gap**: Needs real YouTube API integration

#### `packages/ui-kit/src/components/PlaylistCard.tsx`
**Status**: ✅ Keep - Shared UI component

**Current**: Displays playlist results, used by playlist-web

## 2. Duplicate Code Identification

### 2.1 YouTube API Clients

**Duplicate Found**: 
- `apps/playlist-web/src/lib/youtube.ts` - Full YouTube API client
- `packages/py-core/py_core/data/fetchers.py::fetch_youtube_context()` - Placeholder

**Resolution**:
- ✅ **Keep frontend client** for now (needed for direct API calls)
- ⚠️ **Backend placeholder** needs real implementation
- 🔄 **Future**: Consider extracting shared YouTube client to `packages/js-core` or `packages/py-core`

### 2.2 Topic Parsing

**Duplicate Found**:
- `apps/playlist-web/src/lib/topicParser.ts` - LLM-based parsing
- `apps/playlist-web/src/lib/topicRAG.ts` - RAG-enhanced parsing

**Resolution**:
- ✅ **Keep both** - `topicRAG.ts` extends `topicParser.ts`
- 🔄 **Future**: Move to shared package for reuse by highlight-channel-web

### 2.3 Video Classification

**Duplicate Found**:
- `apps/playlist-web/src/lib/videoClassifier.ts` - Tag classification
- `services/theory-engine-api/app/routers/playlist.py` - Basic classification logic

**Resolution**:
- ✅ **Keep frontend** - More sophisticated
- ⚠️ **Backend** - Needs to use shared logic or call frontend service
- 🔄 **Future**: Extract to shared package

## 3. Dead Code Identification

### 3.1 Debug Routes

**File**: `apps/playlist-web/src/app/api/debug/route.ts`  
**Status**: ❌ **REMOVE** - Development-only debug endpoint

**Reason**: Not needed in production, debug logs should be handled via proper logging

**Action**: Delete file

### 3.2 Debug Logger

**File**: `apps/playlist-web/src/lib/debugLogger.ts`  
**Status**: ⚠️ **CONDITIONAL** - Keep for development, remove from production builds

**Usage**: Only used by debug route (which we're removing)

**Action**: 
- Keep for now (useful for development)
- Add environment check to disable in production
- Or remove if not actively used

### 3.3 Legacy MVP Folder

**Path**: `apps/playlist-web/legacy-mvp/`  
**Status**: 📦 **ARCHIVE** - Keep for reference, mark as deprecated

**Action**: 
- Add `DEPRECATED.md` file in folder
- Document what it was and why it's kept
- Consider moving to `docs/archive/` in future

### 3.4 Unused Imports/Code

**Action**: Run linter to identify unused imports after cleanup

## 4. Code to Refactor into Shared Packages

### 4.1 Core Logic → `packages/js-core` or `packages/py-core`

**High Priority**:
1. **Topic Parsing** (`topicParser.ts`, `topicRAG.ts`)
   - Extract to `packages/js-core/src/topic-parsing/`
   - Or move to Python in `packages/py-core/py_core/playlist/parser.py`
   - Used by: playlist-web, highlight-channel-web (future)

2. **Video Classification** (`videoClassifier.ts`)
   - Extract to `packages/js-core/src/video-classification/`
   - Or Python equivalent
   - Used by: playlist-web, highlight-channel-web (future)

3. **Query Optimization** (`queryOptimizer.ts`)
   - Extract to shared package
   - Used by: playlist-web, highlight-channel-web (future)

**Medium Priority**:
4. **Video Filtering/Scoring** (`videoFiltering.ts`)
   - Extract scoring logic to shared package
   - Keep filtering rules domain-specific

5. **Playlist Building** (`playlistBuilder.ts`)
   - Extract sequencing logic
   - Keep domain-specific rules (sports vs general)

### 4.2 YouTube API Client → Shared Package

**Option A**: Keep in frontend, add backend implementation
**Option B**: Extract to `packages/js-core` for frontend use
**Option C**: Create Python client in `packages/py-core` for backend use

**Recommendation**: 
- Keep frontend client in `apps/playlist-web` for now
- Implement real YouTube API in backend `py_core.data.fetchers`
- Consider shared package later if both need same logic

## 5. Sports Highlight Requirements

### 5.1 New Functionality Needed

1. **Sports Event Parsing**
   - Parse requests like "NFL Week 12 highlights"
   - Extract: sport, league, week/date, event type (highlights/bloopers/upsets)

2. **Date/Time Handling**
   - Parse dates: "Aug 8, 2010", "Week 12", "2023 season"
   - Map to actual dates for YouTube search

3. **Multi-Sport Sequencing**
   - Handle requests like "NFL highlights, then MLB bloopers, then upsets"
   - Sequence multiple sports/events in one playlist

4. **Highlight-Specific Search**
   - Optimize YouTube queries for highlight videos
   - Filter for official channels, highlight reels, top plays

### 5.2 Code Reuse Opportunities

- ✅ **Topic Parsing**: Extend existing parser for sports entities
- ✅ **Video Classification**: Reuse tag system (intro/context/deep_dive/ending)
- ✅ **Playlist Building**: Reuse sequencing logic
- ✅ **YouTube API**: Reuse client, extend search patterns
- ✅ **Caching**: Reuse ContextCache for highlight searches

## 6. Cleanup Actions

### 6.1 Immediate (Step 0)

- [x] Create this audit document
- [ ] Remove `apps/playlist-web/src/app/api/debug/route.ts`
- [ ] Review `debugLogger.ts` usage, disable in production if needed
- [ ] Add deprecation notice to `legacy-mvp/` folder
- [ ] Run linter to find unused imports
- [ ] Update CHANGELOG.md

### 6.2 Phase 1 (Sports Highlight MVP)

- [ ] Create `apps/highlight-channel-web/`
- [ ] Extract topic parsing to shared package
- [ ] Extend backend playlist router for sports mode
- [ ] Implement real YouTube API in backend
- [ ] Add sports event parsing logic

### 6.3 Future Refactoring

- [ ] Move all shared logic to `packages/js-core` or `packages/py-core`
- [ ] Consolidate YouTube API clients
- [ ] Archive or remove `legacy-mvp/` folder
- [ ] Create unified playlist service

## 7. File Inventory

### Keep (Active)
- `apps/playlist-web/src/lib/*.ts` (except debugLogger.ts - conditional)
- `apps/playlist-web/src/app/api/playlist/route.ts`
- `apps/playlist-web/src/app/page.tsx`
- `apps/playlist-web/scripts/get-youtube-token.js`
- `services/theory-engine-api/app/routers/playlist.py`
- `packages/ui-kit/src/components/PlaylistCard.tsx`

### Remove (Dead Code)
- `apps/playlist-web/src/app/api/debug/route.ts` ❌

### Archive (Reference)
- `apps/playlist-web/legacy-mvp/` 📦

### Refactor (Move to Shared)
- Topic parsing logic → `packages/js-core` or `packages/py-core`
- Video classification → shared package
- Query optimization → shared package

## 8. Next Steps

1. **Complete Step 0 cleanup** (this phase)
2. **Create highlight-channel-web app**
3. **Extend backend for sports highlights**
4. **Extract shared logic to packages**
5. **Implement real YouTube API in backend**

---

**Last Updated**: 2024-11-18  
**Next Review**: After Step 0 cleanup complete

