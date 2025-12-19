# Player Modeling (Parked)

Player-level features and filters for v2+.

## Concepts

### Player Minutes
- `player_minutes`: Minutes played for a specific player in a game
- `player_minutes_rolling`: Rolling average of player minutes
- `player_minutes_delta`: Deviation from rolling average

### Player Filters
- Filter games to only those where a specific player participated
- Filter by player role (starter, reserve, etc.)
- Filter by minutes threshold

## Why Parked

1. **Data joins**: Requires boxscore-level player data joins
2. **Sparsity**: Player data is much sparser than team data
3. **Interpretation**: Player impact varies by context
4. **UI complexity**: Player search, autocomplete, validation

## Data Requirements

- `boxscores` table must have player-level rows
- Join path: `games` → `boxscores` → player stats
- Sparsity handling for missing player data

## Future Activation

When ready:
1. Add `FEATURE_PLAYER_MODELING` flag
2. Player filter in DefinePanel
3. Player context features in presets
4. Backend joins in `sports_eda_micro.py`

## Feature Flags

Currently gated by:
```typescript
FEATURE_PLAYER_MODELING = false
```

Enable with:
```bash
NEXT_PUBLIC_FF_PLAYER_MODELING=true
```

## References

- Related context features: `player_minutes`, `player_minutes_rolling`
- Backend stubs exist in `context_presets.py`

