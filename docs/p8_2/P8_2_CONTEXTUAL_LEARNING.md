# P8.2B Contextual Learning

One canonical `KnowledgeUnit` can be projected into an event, feature,
ResearchRun, QuantRun, or StrategySpec through a `KnowledgeContextBinding`.
The binding carries a required why-now sentence, current values, evidence IDs,
dataset fingerprint, context/availability timestamps, and limitations. The
server owns this projection so the browser cannot recompute or silently use
future data.

Quick Explain shows the current value and the shortest safe interpretation.
Teach Me This expands the sequence: why now → prerequisites → intuition →
definition → derivation → controlled example → code → current data → exercise →
literature. Explicit exercise evidence is sent through the existing personal
learning boundary; opening a page alone never records mastery.
