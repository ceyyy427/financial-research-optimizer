# P8.2B SymPy Integration

SymPy is an optional symbolic adapter, not the Finathink mathematical source
of truth. The canonical representation is a bounded `MathExpression` AST;
SymPy may simplify an expression, substitute finite values, compare symbolic
equivalence, and derive TeX from the AST.

The adapter must:

- accept only Finathink AST nodes and named finite substitutions;
- return JSON-safe strings/numbers and a verification label;
- reject arbitrary user LaTeX, Python, `eval`, and `exec`;
- keep optional import failures explicit (`UNAVAILABLE`), never blocking the
  offline catalog or deterministic widgets.

The current core environment is intentionally dependency-light. SymPy is
installed in the isolated math-capability environment for smoke testing and
is exposed through a project `math` extra; it is not required for the core
research fallback.
