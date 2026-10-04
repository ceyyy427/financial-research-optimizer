# P6.6 Educational Code Generation Contract

Educational code is a deterministic explanation artifact generated from a
validated StrategySpec and Strategy IR. It is not the execution representation
and is never automatically run.

Every meaningful block carries trace metadata linking it to a StrategySpec
field, FeatureVersion, or IR node. The generated package includes readable
feature calculations, signal construction, portfolio rule, timing, costs, and
limitations. Static AST checks reject imports, `eval`, `exec`, `compile`,
subprocess, sockets, filesystem writes, dynamic loading, broker names, and
credential access. The export includes the scan result and source fingerprint.
