# Theory Resolution (Parked)

Per-team / per-candidate row modeling for v2+.

## Concepts

### Symmetric vs Directional
- **Symmetric**: Theory applies equally to both teams (e.g., "high-pace games go over")
- **Directional**: Theory favors one side (e.g., "home team covers when rested")

### Candidate Resolution Modes
- **Team-level**: Each game produces one row per team (2 rows per game)
- **Game-level**: Each game is one row with home/away features
- **Side-resolved**: Theory specifies home/away, produces one row per game with outcome based on that side

### Doubled Datasets
When running team-level analysis, the dataset doubles in size. This requires:
- Careful handling of independence assumptions
- Adjusted sample size interpretation
- Different variance calculations

## Why Parked

1. Expands the problem space significantly
2. Requires UI for mode selection that adds cognitive load
3. Interpretation of results varies by mode
4. Current MVP uses game-level (single row) only

## Future Activation

When ready:
1. Add `resolution_mode` to `TheoryDraft`
2. Backend support in `sports_eda_analyze.py`
3. UI toggle in Define panel
4. Results interpretation adjustments

## References

- Design notes from conversation: Dec 2025
- Related: symmetric theories, betting side selection

