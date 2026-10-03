# Finathink P8.2B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a validated, offline-first mathematical knowledge and code pedagogy layer integrated with Finathink research workflows, then prepare and publish the `finathink` identity to the requested GitHub repository.

**Architecture:** Add a standalone `p8_2b` package that composes with existing P7.5/P8.2 contracts. Structured content and deterministic validators are the source of truth; the local server owns context/widgets/exports and the bundled frontend renders them with no-CDN progressive disclosure.

**Tech Stack:** Python 3.11+, frozen dataclasses/enums, stdlib AST/JSON/HTML escaping, optional SymPy adapter, bundled KaTeX or MathJax selected by audit, existing esbuild/Lightweight Charts/ECharts frontend, pytest/Ruff/pip-audit.

**Spec:** `docs/superpowers/specs/2026-10-03-finathink-p82b-design.md` and the user-provided P8.2B mission.

## Global Constraints

- Computer Use is strictly forbidden and no browser-level claim may be made without evidence.
- Canonical math is structured AST; LaTeX/MathML are derived and must work offline.
- No arbitrary Python, shell, network, filesystem, or LLM-generated code execution.
- Existing P7.5/P8.2 contracts and research-only/QMT read-only boundaries remain valid.
- References are metadata-only; fake DOI/citation insertion is rejected.
- Page views do not infer mastery; learning updates require explicit evidence.

## Review Focus

- Malformed AST/LaTeX and non-finite substitutions must fail closed: covered by `tests/p8_2b/test_math.py`.
- Broken/cyclic prerequisites or missing provenance must reject the catalog: covered by `tests/p8_2b/test_catalog.py`.
- Unknown context IDs must not fabricate why-now text: covered by `tests/p8_2b/test_context.py`.
- Code containing imports, calls, file/network/process access, or hidden execution must be rejected: covered by `tests/p8_2b/test_code_trace.py`.
- DOI collisions, invalid identifiers, and offline cache misses must remain deterministic: covered by `tests/p8_2b/test_references.py`.

### Task 1: Identity, capability audit, and package scaffold

**Files:**
- Create: `src/finahinking/p8_2b/__init__.py`, `src/finahinking/p8_2b/identity.py`
- Create: `tests/p8_2b/test_identity.py`
- Modify: `pyproject.toml`, `README.md`, `scripts/clean_install.py`, release metadata as required by tests
- Create: `docs/p8_2/P8_2_MATH_RENDERER_DECISION.md`, `docs/p8_2/P8_2_SYMPY_INTEGRATION.md`

**Interfaces:** `project_identity() -> dict[str, str]`, `finathink` CLI alias, capability records for math renderer/SymPy/CodeMirror/Crossref. Preserve `finahinking` import/CLI compatibility.

- [ ] Probe existing renderer, SymPy, and frontend packages without mutating core.
- [ ] Write failing identity/capability tests.
- [ ] Implement the scaffold, identity alias, and decision reports.
- [ ] Run focused tests and `pip check`.
- [ ] Commit `feat: open p8.2b knowledge engine scaffold`.

### Task 2: Typed math, knowledge, and reference contracts

**Files:**
- Create: `src/finahinking/p8_2b/contracts.py`, `src/finahinking/p8_2b/math.py`, `src/finahinking/p8_2b/references.py`
- Create: `tests/p8_2b/test_contracts.py`, `tests/p8_2b/test_math.py`, `tests/p8_2b/test_references.py`
- Create: `docs/p8_2/P8_2_MATH_DOMAIN_MODEL.md`, `docs/p8_2/P8_2_REFERENCE_ARCHITECTURE.md`

**Interfaces:** frozen JSON-safe `KnowledgeUnit`, `MathExpression`, `SymbolDefinition`, `EquationDefinition`, `DerivationStep`, `Proof`, `CodeBlock`, `CodeSegment`, `DataTrace`, `ReferenceRecord`, `Citation`, and `KnowledgeContextBinding`; AST constructors and `render_latex`, `render_mathml`, `substitute`, `equivalent`; DOI `normalize_doi`, local cache and deterministic exports.

- [ ] Write failing round-trip, AST, DOI, duplicate, and unsafe-input tests.
- [ ] Implement bounded immutable contracts and canonical fingerprints.
- [ ] Implement deterministic AST rendering/substitution/equivalence and reference serialization.
- [ ] Run focused tests and Ruff.
- [ ] Commit `feat: add p8.2b math and reference contracts`.

### Task 3: Curated catalog, validators, flagship lessons, and widgets

**Files:**
- Create: `src/finahinking/p8_2b/catalog.py`, `src/finahinking/p8_2b/validation.py`, `src/finahinking/p8_2b/widgets.py`
- Create: `src/finahinking/p8_2b/content/*.json`
- Create: `tests/p8_2b/test_catalog.py`, `tests/p8_2b/test_validation.py`, `tests/p8_2b/test_widgets.py`
- Create: `docs/p8_2/P8_2_KNOWLEDGE_CONTENT_STANDARD.md`, `docs/p8_2/P8_2_CONTEXTUAL_LEARNING.md`

**Interfaces:** `DEFAULT_KNOWLEDGE_CATALOG`, `validate_catalog`, `search_catalog`, `get_knowledge_unit`, typed widget specs/results for volatility, Sharpe, OLS/Beta, momentum, and OOS split. The four flagship lessons must include why-now placeholders resolved only by context bindings, references, symbols, derivations/proof status, code/data links, misconceptions, assumptions, limitations, and exercises.

- [ ] Write failing catalog completeness/DAG/provenance and exact widget-value tests.
- [ ] Add structured JSON content and load/validate it at startup.
- [ ] Implement deterministic widgets with finite/bounded parameter validation and no execution.
- [ ] Run catalog, widget, and full P8.2B focused tests.
- [ ] Commit `feat: add flagship math knowledge catalog`.

### Task 4: Contextual learning, code pedagogy, learning state, and export

**Files:**
- Create: `src/finahinking/p8_2b/context.py`, `src/finahinking/p8_2b/code.py`, `src/finahinking/p8_2b/pedagogy.py`, `src/finahinking/p8_2b/export.py`
- Create: `tests/p8_2b/test_context.py`, `tests/p8_2b/test_code_trace.py`, `tests/p8_2b/test_learning.py`, `tests/p8_2b/test_export.py`
- Create: `docs/p8_2/P8_2_CODE_PEDAGOGY.md`, `docs/p8_2/P8_2_CODE_MATH_TRACE.md`

**Interfaces:** `resolve_context`, `why_now`, `select_code_segment`, `trace_code_to_data`, `record_learning_evidence`, `learning_sequence`, `export_markdown`, `export_latex`, `export_bibtex`, `export_csl_json`. Reuse existing P6 learning evidence and P8.2 payload IDs.

- [ ] Write failing context/no-context, code line mapping/safety, explicit-learning, and export tests.
- [ ] Implement server-owned context snapshots and static code annotations/traces.
- [ ] Connect explicit exercise evidence to the existing LearningStore without page-view mastery.
- [ ] Implement stable Markdown/LaTeX/BibTeX/CSL exports.
- [ ] Run focused tests and security scans.
- [ ] Commit `feat: connect contextual learning and code traces`.

### Task 5: Local API and UI integration

**Files:**
- Modify: `src/finahinking/local_app.py`
- Modify/Create: `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/knowledge.js`, `frontend/src/research.js`, `frontend/build.mjs`
- Modify: `site/assets/finathink-research.js`
- Create: `tests/p8_2b/test_local_knowledge.py`, `frontend/test/knowledge.test.mjs`
- Create: `docs/p8_2/P8_2_KNOWLEDGE_PEDAGOGY_ARCHITECTURE.md`, `docs/p8_2/P8_2_EDUCATION_ACCESSIBILITY.md`

**Interfaces:** JSON routes for catalog/search/unit/context/widget/export; server-rendered Knowledge concept pages with MathML/LaTeX fallback, why-now/context rail, symbol/derivation/proof disclosure, code line inspector, accessible tables, and no-JS links. `finathink:point-selected` resolves a context binding; browser never recomputes canonical values.

- [ ] Write failing route/HTML/JSON/CSP/no-CDN and pure-node selection tests.
- [ ] Add only the audited bundled renderer dependency if capability gap requires it; do not add CodeMirror without evidence.
- [ ] Implement server payloads, progressive disclosure, keyboard/copy behavior, and research selection integration.
- [ ] Build and run focused frontend/server tests; run `npm audit`.
- [ ] Commit `feat: integrate contextual math learning UI`.

### Task 6: Documentation and P8.2B gate

**Files:**
- Create: `docs/p8_2/P8_2_EDUCATION_FINAL_VALIDATION.md`
- Modify: `docs/PROJECT_STATE.md`, `README.md`, `CHANGELOG.md`, `DEPENDENCY_RECORD.md`, `EVOLUTION_LOG.md`, governance validators/tests
- Create: `scripts/p8_2b_education_smoke.py` and tests as needed

- [ ] Run core/quant full suites, P8.2B focused suites, Ruff, notebook, pip-audit, secret scan, governance, clean wheel install, frontend build/tests/perf, and optional smoke checks.
- [ ] Review every education-gate item; mark PASS only with evidence and NOT VERIFIED where browser/live metadata evidence is unavailable.
- [ ] Run a fresh independent review of the clean tree; correct any P0/P1 findings.
- [ ] Commit `docs: record p8.2b education validation` and create local tag `p8-2b-local-validated`.

### Task 7: GitHub identity and publication

**Files:**
- Modify: `pyproject.toml`, `README.md`, package/release metadata, remote configuration, docs links as required
- Create/Modify: `.github/workflows/ci.yml`, release notes only if required by verified repository state

- [ ] Confirm target repository identity and authentication with read-only GitHub checks.
- [ ] Update project ID to `finathink` while preserving import compatibility and add `finathink` CLI.
- [ ] Run final clean-install, audit, secret, diff, and status checks.
- [ ] Push only the reviewed local branch to the requested target, never force-push unrelated history.
- [ ] If the user’s requested repository slug must be renamed, use the authenticated GitHub API only after the final local gate and record the new URL.
- [ ] Verify the resulting remote commit/CI/release state and write the publication record.
