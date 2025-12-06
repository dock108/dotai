# Feature Builder Layers (Phase 3)

Layers
- Level 0 (Required): closing odds/lines, final score, basic metadata.
- Level 1 (Domain): ratings, projections, pace metrics (when available).
- Level 2 (Derived): deltas, rolling/z-scores/volatility, implied vs actual probability gaps.

Builders
- `engine.common.feature_layers.Level0RequiredBuilder`
- `engine.common.feature_layers.Level1DomainBuilder`
- `engine.common.feature_layers.Level2DerivedBuilder`
- `engine.common.feature_layers.CombinedFeatureBuilder`
- Factory: `engine.common.feature_layers.build_combined_feature_builder(mode="admin"|"full")`

Modes
- Admin mode: Level 0 only (fast validation).
- Full mode: Levels 0–2 (model-ready).

EDA integration
- `feature_mode` (admin|full) is optional on preview/analyze/build-model requests.
- When set, the API merges layered features into the computed matrix (alongside selected generated features).

Adding new domain builders
- Extend the existing Level 1/2 builders or add a new FeatureBuilder subclass.
- Return only available keys; raise nothing (CombinedFeatureBuilder swallows errors for speed).

