# Feature Categories

Features in the Theory Builder are organized by semantic purpose, not technical derivation.

## Categories

### 1. Measurement Fields (Always Computed)
Core outcome data derived from games/odds. Never shown as selectable "features."

```python
MEASUREMENT_FIELDS = {
    "home_score", "away_score", "combined_score", "margin_of_victory",
    "closing_spread_home", "closing_total", "did_home_cover", "total_result",
    "winner", "closing_ml_home", "closing_ml_away"
}
```

### 2. Concept Fields (Auto-Derived)
Computed only when the concept is referenced in the theory:

| Concept | Fields | Trigger |
|---------|--------|---------|
| Pace | `pace_game`, `pace_home_possessions`, `pace_away_possessions` | "pace" in inputs |
| Rest | `home_rest_days`, `away_rest_days`, `rest_advantage` | Rest filter enabled |
| Altitude | `altitude_ft`, `altitude_delta` | Altitude-related inputs |

### 3. Context Features (User-Selected via Presets)
Optional features selected through presets or custom toggles:

| Category | Examples |
|----------|----------|
| Game | `conference_game`, `is_back_to_back`, `days_rest` |
| Market | `closing_spread`, `closing_total`, `implied_prob`, `line_movement` |
| Team | `rating_diff`, `elo_delta`, `projection_spread` |
| Player | `player_minutes`, `player_minutes_rolling` |
| Diagnostic | `cover_margin`, `total_delta` (post-game, leaky) |

## Context Presets

| Preset | Game | Market | Team | Player | Diagnostic |
|--------|------|--------|------|--------|------------|
| Minimal | — | — | — | — | — |
| Standard | ✓ | — | — | — | — |
| Market-aware | ✓ | ✓ | — | — | — |
| Player-aware | ✓ | ✓ | — | ✓ | — |
| Verbose | ✓ | ✓ | ✓ | ✓ | — |
| Custom | (user picks) | | | | |

Diagnostic features are gated behind an explicit toggle with warning text.

## Feature Policy

The `feature_policy` field in `TheoryDraft.inputs` controls feature derivation:

- **auto** (default): Backend expands `base_stats × featurePolicy × context.features`
- **manual**: UI specifies exact feature list (advanced use only)

## Base Stats → Features

When a user selects base stats (e.g., `fg3_pct`, `turnovers`), the backend automatically generates:

| Variant | Example | Description |
|---------|---------|-------------|
| Raw | `home_fg3_pct`, `away_fg3_pct` | Per-team values |
| Combined | `combined_fg3_pct` | Sum or average |
| Differential | `diff_fg3_pct` | Home minus away |
| Rolling | `home_fg3_pct_5g` | 5-game rolling average |

The UI never exposes this taxonomy—users just pick stats and the backend handles derivation.

## Target Leakage Protection

Features that directly proxy the target are automatically excluded:

| Target | Excluded Features |
|--------|-------------------|
| `combined_score` | `final_total_points`, `total_delta` |
| `did_home_cover` | `cover_margin`, `ats_result` |
| `winner` | `margin_of_victory` |

In "deployable" mode, all post-game features are dropped to ensure the model uses only pre-game data.
