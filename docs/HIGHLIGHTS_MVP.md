# Sports Highlight MVP - Constraints, Limitations, and Future Ideas

## Current Constraints

### Technical Constraints

1. **YouTube API Limits**
   - Free tier: 10,000 units per day
   - Each search = 100 units, each video details = 1 unit
   - Typical playlist generation: ~200-300 units per request
   - Caching is critical to stay within limits

2. **Content Availability**
   - Only returns videos available on YouTube
   - Relies on official channels and major networks for quality
   - No control over video availability or removal

3. **Parsing Accuracy**
   - AI parsing may misinterpret ambiguous requests
   - Date parsing can be inconsistent (e.g., "last night" vs specific dates)
   - Sport detection may fail for obscure sports or non-English queries

4. **Duration Matching**
   - Target duration has ±10% tolerance
   - May not find enough content for very specific requests
   - No guarantee of exact duration match

### Legal/Content Constraints

1. **No Content Hosting**
   - We do not host or control any video content
   - All videos are links to YouTube
   - Users must comply with YouTube's terms of service

2. **Copyright Compliance**
   - Only links to publicly available YouTube videos
   - Blocks requests for full game reuploads, PPV content, pirated broadcasts
   - Cannot provide downloads or bypass YouTube's platform

3. **Trademark Compliance**
   - No use of "SportsCenter" or other trademarked branding
   - Generic "sports highlights" terminology only

4. **Limited Internationalization**
   - Primarily English-language content
   - Sport names and team names must be in English
   - No support for non-English YouTube content

## Future Ideas

### Short-term Enhancements

1. **Team/League Personalization**
   - Save favorite teams/leagues per user
   - Quick access buttons for "My Teams"
   - Personalized playlist suggestions

2. **Content Mix Slider**
   - Visual slider for highlights vs bloopers ratio
   - Fine-grained control over content types
   - Preview of content mix before generation

3. **Real-time Playlist Updates**
   - Webhook notifications when new videos match criteria
   - Auto-refresh playlists for recent events (< 2 days old)
   - Push notifications for favorite teams

4. **Video Quality Filtering**
   - Filter by resolution preference
   - Prefer official channels (higher quality)
   - Quality score in video metadata

### Medium-term Enhancements

1. **Music Integration**
   - Mix in background music tracks
   - Genre selection (hip-hop, rock, electronic)
   - Sync music to highlight tempo

2. **Multi-sport Playlists**
   - "Best of all sports today" playlists
   - Cross-sport comparisons
   - Unified scoring across sports

3. **Social Features**
   - Share playlists with friends
   - Public playlist gallery
   - Comments and ratings

4. **Advanced Filtering**
   - Filter by player names
   - Filter by game type (regular season, playoffs, championships)
   - Filter by highlight type (game-winning plays, upsets, comebacks)

### Long-term Vision

1. **AI-Generated Highlights**
   - Use AI to identify key moments in full games
   - Auto-generate highlight reels from game footage
   - Custom highlight packages per user preference

2. **Betting Integration**
   - Link playlists to betting models
   - "Watch highlights for the game you're modeling"
   - Historical highlight analysis for betting insights

3. **Theory Engine Integration**
   - Use highlight playlists as data source for conspiracy/theory engine
   - Analyze patterns across highlight playlists
   - Generate theories based on highlight trends

4. **Mobile App**
   - Native iOS/Android apps
   - Background playlist generation
   - Offline playlist caching

5. **Live Highlights**
   - Real-time highlight detection during live games
   - Auto-update playlists as games progress
   - Live highlight notifications

## Technical Debt

1. **Caching Strategy**
   - Current staleness logic is simple time-based
   - Could be improved with event-based staleness
   - Need better cache invalidation on schema changes

2. **Error Handling**
   - YouTube API rate limiting not fully handled
   - No retry logic for transient failures
   - Limited error messages for users

3. **Testing**
   - Limited unit tests for scoring logic
   - No integration tests for full playlist generation
   - Need test fixtures for YouTube API responses

4. **Monitoring**
   - Basic logging in place, but no alerting
   - No dashboard for real-time metrics
   - Need better error tracking and reporting

