# P8.2B Code Pedagogy

Code examples are read-only learning objects. A segment has a bounded line
range, input/output descriptions, equation IDs, feature IDs, and a finance
role. The inspector can explain one line without executing it. The validator
uses Python's parser only to reject syntax errors and unsafe imports/calls;
there is no `eval`, shell, filesystem, network, or arbitrary notebook path.

Controlled widgets are the only runnable examples. They accept typed,
finite, bounded parameters and return scalar/series summaries from known
calculations. This keeps a learner's path inspectable and reproducible.
