# Finathink P8.2B Knowledge and Pedagogy Architecture

P8.2B treats a lesson as a versioned, inspectable knowledge unit rather than
an unstructured prompt. The unit is stored as JSON-safe contracts and loaded
through `KnowledgeCatalog`; the canonical formula is a bounded math AST.
LaTeX, MathML, and KaTeX HTML are renderings, never the source of truth.

## The learning path

Every flagship unit exposes the same sequence:

1. **Why now and history** — the learner sees the current research question,
   background, and the historical reason the concept matters.
2. **Symbols and intuition** — notation, units, plain-language meaning, and
   a deliberately bounded intuition are shown before manipulation.
3. **Equation and derivation** — each equation has an AST, rendered LaTeX and
   MathML, assumptions, derivation steps, and a proof boundary.
4. **Code and data** — reviewed static code segments link to equation IDs,
   feature IDs, input, and output. The application never executes arbitrary
   learner code.
5. **Finance and strategy interpretation** — applications are labeled as
   interpretations and limitations, not recommendations.
6. **Current context** — a point-in-time binding may attach current values,
   evidence IDs, feature identity, a ResearchRun, availability time, and the
   dataset fingerprint. Without a valid binding the UI says
   `NO_CONTEXT_AVAILABLE`.

The UI supports a quick visual path and a deep path, but browsing alone does
not infer mastery. Learning evidence is recorded explicitly through the
existing private learning store.

## Safety and reproducibility

- Content validation rejects unknown prerequisites, missing equation links,
  broken derivation/proof references, missing citations, unsafe code, and
  future `available_at` timestamps.
- Widgets are typed allow-list calculations for volatility, Sharpe, OLS,
  momentum, and OOS splitting. Inputs are finite and bounded; there is no
  `eval`, `exec`, shell, network, or arbitrary Python path.
- References are metadata records with normalized DOI, duplicate detection,
  local cache state, BibTeX, and CSL JSON export. A DOI is not presented as
  verified full text, and live Crossref is optional rather than a CI
  dependency.
- The server renders a MathML/no-JavaScript fallback. KaTeX is bundled
  locally for the enhanced visual path, so the lesson remains offline and
  same-origin.

## Flagship coverage

The initial catalog covers volatility, OLS, Sharpe ratio, momentum, and
out-of-sample overfitting. These units share the same contract and are
intentionally small enough to audit line-by-line before expanding the
curriculum.

