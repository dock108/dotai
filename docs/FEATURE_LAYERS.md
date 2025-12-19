# Feature Handling (MVP)

The Theory Builder handles features internally. Users just pick stats—no feature engineering exposed.

## How It Works

1. **User picks stats** (e.g., `turnovers`, `fg3_pct`)
2. **Backend auto-generates variants** (raw, diff, combined)
3. **Results show correlations** with human-readable names

## Context Presets

| Preset | What's Added | When to Use |
|--------|--------------|-------------|
| Minimal | Nothing | Pure stat analysis |
| Standard | Pace, conference | Most theories |
| Market-aware | + closing lines | When line matters |

That's it for MVP. No exposed feature taxonomy.

---

## Internal Details (Not Exposed in MVP UI)

### Feature Categories

- **Measurement Fields**: Outcomes (scores, cover results) - always computed, never shown as features
- **Concept Fields**: Auto-derived when referenced (pace, rest) - computed silently
- **Context Features**: Added via presets - user doesn't see individual toggles

### Target Leakage Protection

Features that proxy the target are automatically excluded:

| Target | Excluded |
|--------|----------|
| `spread_result` | `cover_margin`, `ats_result` |
| `game_total` | `final_total_points`, `total_delta` |
| `moneyline_win` | `margin_of_victory` |

### Parked Features

See `/future/` for:
- Player-level features (`player_minutes`, `player_minutes_rolling`)
- Custom feature selection
- Post-game diagnostics
- Nonlinear bucketing
