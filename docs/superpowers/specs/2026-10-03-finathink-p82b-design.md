# Finathink P8.2B Mathematical Knowledge and Code Pedagogy Design

## Outcome

Extend the existing P7.5 Knowledge Engine and P8.2 research workspace into a
source-backed, offline-first learning layer that connects current data,
mathematics, code, finance, strategy, and literature without introducing
arbitrary code execution or a second learning-state machine.

## Boundaries

- The existing `finahinking` Python import namespace remains compatible; the
  public project identity and CLI gain the canonical `finathink` name.
- P8.2B owns additive contracts in `src/finahinking/p8_2b/`; it does not replace
  P7.5 knowledge or P8.2 research contracts.
- Canonical mathematics is a validated expression AST. LaTeX, MathML, and
  plain text are derived renderings.
- Mathematical rendering is bundled and offline. One primary renderer is
  admitted after an audit; no CDN is required.
- References are metadata-only, locally cached, DOI-normalized, and source
  classified. Crossref resolution is optional and never required for offline
  use.
- Code examples are read-only and statically inspected. Controlled examples
  use allow-listed deterministic calculations; arbitrary Python, shell,
  network, and filesystem execution are forbidden.
- Context bindings reuse existing event, feature, ResearchRun, QuantRun,
  StrategySpec, and LearningStore identifiers. A page view never implies
  mastery.
- The flagship catalog contains OLS, Sharpe, Momentum, and OOS/Overfitting;
  Returns/Volatility provide the shared data and prerequisite path.

## Architecture

`KnowledgeUnit` is the aggregate root. It contains symbols, AST-backed
equations, derivation/proof steps, assumptions, limitations, curated code
segments, deterministic data traces, applications, misconceptions, references,
and learning activities. `KnowledgeContextBinding` projects one unit into an
event, research, feature, or strategy context and carries a required why-now
statement plus current values and evidence IDs.

The server owns validation, catalog lookup, context resolution, widget
calculation, and export. The browser receives JSON-safe payloads and renders
the same canonical values. The no-JavaScript HTML path remains usable. A
bundled math renderer exposes accessible MathML where supported, and the UI
offers symbol inspection, equation references, derivation disclosure, code
line selection, and math/code/data navigation.

## Quality and release gates

The catalog validator rejects missing provenance, broken prerequisite links,
cyclic prerequisites, invalid derivation references, malformed DOI metadata,
and unsafe executable code. Deterministic tests cover AST rendering,
substitution, widget bounds, code trace links, context resolution, learning
state evidence, citation export, and no-CDN/offline assets. Existing P8.2
tests and gates must remain green. Browser paint, screen-reader timing, live
Crossref, and real QMT remain explicitly labeled when unavailable.

After the local P8.2B gate passes, project identity is updated to `finathink`,
the target GitHub repository is configured, a final clean-install/audit pass
is run, and only then is a push or repository rename attempted. A GitHub login
prompt is the only expected human intervention during publication.
