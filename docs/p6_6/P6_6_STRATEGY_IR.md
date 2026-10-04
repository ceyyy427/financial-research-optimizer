# P6.6 Strategy IR

The Strategy IR is a constrained, serializable intermediate representation.
Its node kinds are limited to registered feature references, comparisons,
boolean combinations, ranks, selection, target-weight construction, rebalance,
and next-period execution. Parameters are finite JSON values with bounded
windows, thresholds, fractions, and weights.

The IR has no fields for Python source, callable objects, imports, paths, URLs,
SQL, shell commands, credentials, broker APIs, or dynamic module names. Its
fingerprint covers the StrategyVersion, FeatureGraph fingerprint, node list,
and compiler version. Only the internal compiler can turn it into a P5
`Strategy` adapter.
