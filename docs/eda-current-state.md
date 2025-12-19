# Theory Builder (Dec 2025)

Admin-only Theory Builder for sports betting analysis. MVP scope: game-level ATS/Totals/ML analysis.

## MVP Surface

What the user sees:

1. **Pick market** (ATS / Totals / ML)
2. **Pick stats** to analyze
3. **Run**
4. **See results**:
   - Does it matter? (lift %)
   - How much? (sample size)
   - Is it plausible? (assessment)
   - Sample games

What the user does **not** see:
- How the sausage is made (feature engineering)
- Bet sizing / staking logic
- Automation / triggers
- Player-level nuance
- Nonlinear diagnostics

## Architecture

### Frontend Components

Located at `apps/theory-bets-web/src/components/admin/theory-builder/`:

| Component | Purpose |
|-----------|---------|
| `TheoryBuilderPage.tsx` | Root component, manages tabs |
| `useTheoryBuilderState.ts` | Single source of truth for `TheoryDraft` state |
| `DefinePanel.tsx` | League, Target, Stats, Context |
| `RunPanel.tsx` | Analyze button (Model/MC hidden via flags) |
| `ResultsPanel.tsx` | Summary, assessment, sample games, correlations |
| `LeagueSelector.tsx` | League dropdown |
| `TimeWindowSelector.tsx` | Time window presets |
| `TargetSelector.tsx` | Market type cards (ATS/Totals/ML) |
| `BaseStatsSelector.tsx` | Stat chips |
| `ContextPresetSelector.tsx` | Context dropdown (Minimal/Standard/Market-aware) |

### Feature Flags

Located at `apps/theory-bets-web/src/lib/featureFlags.ts`:

| Flag | Status | Description |
|------|--------|-------------|
| `FEATURE_STABILITY_BREAKDOWN` | hidden | Stability by season (needs charts) |
| `FEATURE_MONTE_CARLO` | hidden | MC simulation (too much implied authority) |
| `FEATURE_BET_SIMULATION` | hidden | Triggers, exposure controls |
| `FEATURE_ROI` | hidden | ROI units (staking logic not finalized) |
| `FEATURE_MODEL_BUILDING` | hidden | Model training button |
| `FEATURE_PLAYER_MODELING` | hidden | Player filters and features |
| `FEATURE_TEAM_STAT_TARGETS` | hidden | Non-market stat targets |
| `FEATURE_CUSTOM_CONTEXT` | hidden | Custom feature toggles |
| `FEATURE_DIAGNOSTICS` | hidden | Post-game diagnostic features |

Enable any flag with: `NEXT_PUBLIC_FF_<FLAG_NAME>=true`

## TheoryDraft Schema (MVP subset)

```typescript
interface TheoryDraft {
  league: string;           // "NBA", "NFL", "NCAAB", etc.
  time_window: {
    mode: "current_season" | "last_30" | "last_60";
    value?: number;
  };
  target: {
    type: "spread_result" | "game_total" | "moneyline_win";
    side?: "home" | "away" | null;
  };
  inputs: {
    base_stats: string[];
  };
  context: {
    preset: "minimal" | "standard" | "market_aware";
  };
  filters: {
    team?: string;
    phase?: "out_conf" | "conf" | "postseason";
    spread_abs_min?: number;
    spread_abs_max?: number;
  };
}
```

## User Flow (MVP)

### Define Tab
1. **League**: NBA, NFL, NCAAB, etc.
2. **Time window**: This season, Last 30 days, Last 60 days
3. **Market**: Spread (ATS), Totals (O/U), or Moneyline
4. **Stats**: Select the stats to analyze
5. **Context**: Minimal, Standard, or Market-aware

### Run Tab
- **Analyze**: Run correlation analysis

### Results Tab
- **Summary sentence**: "Games matching this theory covered 54.2% vs 50% baseline (+4.2% lift)"
- **Assessment**: ✓ Meaningful lift, ✓ Good sample, etc.
- **Sample games**: Date, Home/Score, Away/Score, Target, Result
- **Correlations**: Collapsed, diagnostic framing
- **Export**: JSON download

## Parked Features

Design notes in `/future/`:
- `/future/theory-resolution/` - Per-team row modeling
- `/future/player-modeling/` - Player-level features
- `/future/nonlinear-analysis/` - Bucketing and monotonic analysis

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/admin/sports/eda/stat-keys/{league}` | Available stat keys |
| `POST /api/admin/theory/analyze` | Run analysis |

Model/MC endpoints exist but are not exposed in MVP UI.
