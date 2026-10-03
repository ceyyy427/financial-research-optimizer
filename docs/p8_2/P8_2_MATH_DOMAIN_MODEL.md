# P8.2B Math Domain Model

The education engine stores a bounded expression AST instead of treating
LaTeX as its authority. Nodes are symbols, finite numbers, unary negation,
binary operations (`+`, `-`, `*`, `/`, `^`), and a small allow-list of
functions. Each `EquationDefinition` names its symbols and meaning; a
`DerivationStep` records what changed, why it is valid, the rule used, and the
assumptions. Proofs carry an honest verification status.

Derived views include LaTeX, MathML, plain text, finite substitutions, and
deterministic numeric examples. SymPy is optional and can label an equivalence
as `SYMBOLICALLY_VERIFIED`; the AST fallback remains explicit when it is not
available. No arbitrary expression parsing or generated code execution is
part of the model.
