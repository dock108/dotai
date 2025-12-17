# Theory Builder (Dec 2025)

Admin-only Theory Builder for sports betting analysis. Replaces the old EDA/Modeling Lab with a cleaner, intent-driven flow.

## Architecture

### Frontend Components

Located at `apps/theory-bets-web/src/components/admin/theory-builder/`:

| Component | Purpose |
|-----------|---------|
| `TheoryBuilderPage.tsx` | Root component, manages tabs and validation |
| `useTheoryBuilderState.ts` | Single source of truth for `TheoryDraft` state |
| `DefinePanel.tsx` | Scope, Target, Inputs, Context configuration |
| `RunPanel.tsx` | Analyze, Build Model, Monte Carlo actions |
| `ResultsPanel.tsx` | Summary, verdict, correlations, sample games |
| `LeagueSelector.tsx` | League dropdown |
| `TimeWindowSelector.tsx` | Time window presets + custom range |
| `TargetSelector.tsx` | Target type cards with accessible ARIA |
| `BaseStatsSelector.tsx` | Collapsible stat chips with explicit selection |
| `ContextPresetSelector.tsx` | Preset dropdown + custom feature toggles |

### Backend Endpoints

Located at `services/theory-engine-api/app/routers/`:

| Endpoint | Description |
|----------|-------------|
| `GET /api/admin/sports/eda/stat-keys/{league}` | Available stat keys for a league |
| `POST /api/admin/theory/analyze` | Run analysis on a `TheoryDraft` |
| `POST /api/admin/theory/build-model` | Train model (market targets only) |
| `POST /api/admin/sports/eda/analysis-runs` | List persisted runs |
| `POST /api/admin/sports/eda/walkforward` | Rolling train/test replay |

## TheoryDraft Schema

The canonical JSON shape that flows from UI to backend:

```typescript
interface TheoryDraft {
  league: string;                    // "NBA", "NFL", "NCAAB", etc.
  time_window: {
    mode: "current_season" | "last_30" | "last_60" | "last_n" | "custom";
    value?: number;
    start_date?: string;
    end_date?: string;
  };
  target: {
    type: "game_total" | "spread_result" | "moneyline_win" | "team_stat";
    stat?: string;
    metric: "numeric" | "binary";
    side?: "home" | "away" | null;   // Optional - only if theory is side-specific
  };
  inputs: {
    base_stats: string[];            // User-selected stats
    feature_policy: "auto" | "manual";
  };
  context: {
    preset: "minimal" | "standard" | "market_aware" | "verbose" | "custom";
    features: {
      game: string[];
      market: string[];
      team: string[];
      player: string[];
      diagnostic: string[];
    };
  };
  filters: {
    team?: string;
    player?: string;
    phase?: "out_conf" | "conf" | "postseason";
    spread_abs_min?: number;
    spread_abs_max?: number;
  };
  diagnostics: {
    allow_post_game_features: boolean;
  };
  model: {
    enabled: boolean;
    prob_threshold: number;
  };
}
```

## User Flow

### Define Tab
1. **Scope**: Pick league + time window (presets: This season, Last 30/60 days, Custom)
2. **Target**: Click card for outcome type (Game total, Spread result, Moneyline, Team stat)
3. **Inputs**: Select base stats (collapsible with summary when selected)
4. **Context**: Choose preset (Minimal, Standard, Market-aware) or customize

### Run Tab
- **Analyze**: Run correlation analysis (enabled when target + ≥1 stat selected)
- **Build Model**: Train logistic regression (market targets only, requires analysis)
- **Monte Carlo**: Simulate bet outcomes (requires model)

### Results Tab
- **Summary sentence**: Human-readable lift description
- **Assessment**: Structured verdict with checkmarks (lift, sample size, stability)
- **Sample games**: Table with Date, Home/Score, Away/Score, Target, Result
- **Correlations**: Collapsed by default, diagnostic framing
- **Export**: Full analysis JSON download

## Validation Rules

| Condition | Result |
|-----------|--------|
| No target selected | Run tab disabled |
| No stats selected | Run tab disabled |
| Target + ≥1 stat | "✓ Ready" indicator, Run tab enabled |
| Analysis complete | Results tab enabled |
| Market target + analysis | Model/MC buttons enabled |
| Stat target | Model/MC disabled (stat analysis is complete at evaluation) |

## Context Presets

| Preset | Includes |
|--------|----------|
| Minimal | None |
| Standard | `conference_game`, `rest_days` |
| Market-aware | Standard + `closing_spread`, `closing_total`, `implied_prob` |
| Player-aware | Market-aware + `player_minutes`, `player_minutes_rolling` |
| Verbose | All available features |
| Custom | User-selected |

## Concept Detection

The backend automatically detects patterns from theory inputs:

| Concept | Derived Fields | Trigger |
|---------|----------------|---------|
| Pace | `pace_game`, `pace_home_possessions`, `pace_away_possessions` | "pace" in inputs or pace filters |
| Rest | `home_rest_days`, `away_rest_days`, `rest_advantage` | `include_rest_days` filter |
| Altitude | `altitude_ft`, `altitude_delta` | Altitude-related inputs |

## Persistence

- Runs stored via micro store with UUIDs
- `EDA_RUNS_DIR` (default `/tmp/eda_runs`) for CSV artifacts
- Endpoints: `GET /analysis-runs`, `GET /analysis-runs/{id}`

## Migration from Old EDA

The old EDA components have been deleted:
- `TheoryForm.tsx` → `DefinePanel.tsx`
- `ResultsSection.tsx` → `ResultsPanel.tsx`
- `FeatureListPanel.tsx` → Removed (features auto-derived)
- `PipelineTabs.tsx` → Tab logic in `TheoryBuilderPage.tsx`
- `page.module.css` → `TheoryBuilder.module.css`

The new UI emits only the `TheoryDraft` JSON shape. Legacy translation is handled server-side during transition.
