# P8.2B Code–Math–Data Trace

The trace is a directed explanation edge:

`CodeSegment → EquationDefinition → FeatureDefinition (optional) → data input/output → finance role → limitations`.

Selecting a code segment never reruns it. It returns the source line, linked
equation IDs, feature IDs, declared input/output, and the unit's limitations.
The reverse path starts at an equation and highlights its curated code segment
through the same IDs. New strategy code must be represented as a reviewed
`StrategySpec`/trace before it can appear as canonical teaching material.
