# P6.6 Feature Contract

`FeatureDefinition` is an immutable, JSON-safe description of one calculation.
It includes `feature_id`, `name`, `description`, `category`, `formula`,
`input_fields`, `source_requirements`, `window`, `lag`, `normalization`,
`missing_policy`, `availability_rule`, `cross_sectional_scope`, `parameters`,
and `version`. This is the point-in-time feature contract.

`FeatureVersion` fingerprints the complete definition. Changing formula,
window, lag, normalization, missing policy, or source rule creates a new
version. A `FeatureVersion` is never silently mutated.

Supported first primitives are `return`, `rolling_mean`, `rolling_volatility`,
`momentum`, `cross_sectional_rank`, `z_score`, `threshold`, and `interaction`.
Each primitive has deterministic window, lag, missing-value, and availability
semantics. Feature values may only use rows whose `available_at` is no later
than the feature signal time.

The registry is deliberately small. Unsupported names, dynamic expressions,
future-looking availability rules, negative windows, and unbounded parameters
are rejected.
