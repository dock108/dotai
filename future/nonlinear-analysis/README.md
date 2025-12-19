# Nonlinear Analysis (Parked)

Bucketing and monotonic analysis for v2+.

## Concepts

### Bucketing Stats
Divide a continuous stat into buckets to find non-linear relationships:
- "Does outcome improve monotonically with stat?"
- "Is there an optimal range for this stat?"
- "Are there threshold effects?"

Example: `turnovers` bucketed into [0-5], [6-10], [11-15], [16+]
→ Visualize hit rate by bucket to see if relationship is linear

### Monotonic Analysis
Test if relationship between feature and outcome is monotonic:
- Strictly increasing?
- Strictly decreasing?
- Non-monotonic (suggests interaction or threshold)?

### Shape Inspection
- Line charts of bucketed performance
- Confidence intervals per bucket
- Comparison to baseline by bucket

## Why Parked

1. **EDA-heavy**: More exploratory than production-ready
2. **Overinterpretation risk**: Bucketing can create false patterns
3. **UI complexity**: Requires visualization components
4. **Multiple comparisons**: More tests = more false positives

## Future Activation

When ready:
1. Add bucket controls to advanced section
2. Backend bucketing logic
3. Chart components for visualization
4. Monotonicity tests with confidence intervals

## Implementation Notes

- Could use Jupyter notebook for initial exploration
- Consider significance correction for multiple buckets
- Bucket boundaries should be data-driven (percentiles)

## References

- Related: feature correlations, lift analysis
- Potential library: scipy for monotonicity tests

