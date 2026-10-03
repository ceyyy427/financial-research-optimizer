# Evolution Log

## 2026-10-02 — P4 experiment engine

- Added deterministic ResearchRun, ExperimentEngine, and local RunStore.
- Added canonical JSON and dataset/result fingerprints for reproduction.
- Added no dependency; recorded the decision in DEPENDENCY_PROPOSAL.md.
- Stopped at P4 for human review as required.

Record material architecture and governance changes here. Each entry should
state the date, change, reason, evidence, compatibility impact, and review
result. Small documentation corrections may be grouped in one entry.

## 2026-10-03 — P6.6 contract repair and P7 private intelligence

- Change: repaired P6.6 threshold/rank/window/configuration parity and explicit
  panel-paper behavior; added the additive P7 migration, owner-scoped private
  graph, explainable mastery, history, consented projections, and room-scoped
  evidence-linked community slice.
- Reason: close the final P6.6 contract defects before adding the user's
  personal continuity and evidence-driven community layer.
- Evidence: focused P6.6 contract tests, P7 vertical tests, full dual
  environment suites, Ruff, notebook, governance, pip, and PostgreSQL
  migration checks recorded in the P6.6/P7 final validation reports.
- Compatibility: no new dependency, plugin, broker SDK, or live execution;
  migration 003 is additive and existing P0–P6.6 authorities remain the
  calculation/provenance source of truth.
- Review: P7 independent A–J reviews and security/privacy/data-quality/
  reproducibility documents are recorded; P8 is readiness-only.

## 2026-10-03 — requested delivery stops at P3

- Change: re-established P0–P3 as the authoritative delivery boundary and
  added a P3 completion report plus validator coverage for the stop state.
- Reason: the user requested autonomous completion through P3 and a pause for
  human inspection; later phase files are retained but must not be treated as
  current gate evidence.
- Evidence: `docs/FINAHINKING_P3_COMPLETION_REPORT.md`, the four phase gate
  reviews, governance tests, and the fresh P0–P3 validation commands recorded
  in that report.
- Compatibility: no later-phase files were deleted or rewritten; current
  README, architecture, and contribution guidance now point to P3.
- Review: P0–P3 are the only gates in scope; P4+ is waiting for explicit human
  approval.

## 2026-10-02 — P5.5 quant platform stabilization

- Change: froze six Finathinking-owned quant service contracts; added complete
  validity classifications, explicit OOS/freeze boundaries, multiple-testing
  metadata, structured realism warnings, and a deterministic cross-sectional
  lagged-momentum multi-asset slice with ResearchRun/QuantRun/Artifact
  provenance.
- Reason: make P5's research-only calculations a stable, agent-safe boundary
  before adding guided user workflows.
- Evidence: `docs/p5_5/P5_5_FINAL_VALIDATION_REPORT.md`,
  `docs/p5_5/P6_READINESS_REPORT.md`, P5.5 fixtures/tests, and independent
  architecture/security/quant-validity/reproducibility review.
- Compatibility: additive modules preserve all P5 contracts; no core
  dependency or plugin/MCP installation; statsmodels remains isolated.
- Review: P5.5 Gate A PASS; P6 may begin; P7 remains waiting for human approval.

## 2026-10-02 — P6 guided quant research and learning

- Change: added typed question classification, explicit hypotheses and
  assumption review, plan-bound quant tool execution, grounded explanations,
  predict → reveal → explain, learning cards/state, and an isolated
  regression-learning workflow.
- Reason: make the stabilized quant platform understandable and safely usable
  by a human without turning the AI layer into a source of quantitative truth.
- Evidence: `docs/p6/P6_FINAL_VALIDATION_REPORT.md`,
  `docs/p6/P6_GATE_REVIEW.md`, 136 deterministic test cases (one environment-
  appropriate skip), notebook/governance/Ruff/pip gates, and independent
  architecture/security/validity/explanation/reproducibility passes.
- Compatibility: P5/P5.5 contracts remain additive and deterministic; no new
  dependency, plugin, MCP server, market-data provider, or agent framework was
  installed. `statsmodels` remains isolated.
- Review: P6 Gate PASS; project stops here and P7 remains WAITING FOR HUMAN
  APPROVAL.

## 2026-10-03 — P6.5 understanding engine / product reality integration

- Change: added a bounded, source-admitted BLS CPI capture/replay slice;
  immutable canonical observations and revisions; explicit temporal fields;
  normalized event, claim, evidence, concept, hypothesis, and learning links;
  a parameterized SQLite adapter plus PostgreSQL migration gate; and a
  progressive Event → Mechanism → Evidence → Quant → Deep Knowledge journey.
- Reason: prove that a real person can inspect a real financial event, see its
  evidence and limitations, test one typed historical idea through the frozen
  P6 gateway, and retain a grounded learning artifact without turning the
  system into a trading or forecasting service.
- Evidence: `docs/p6_5/P6_5_GATE_REVIEW.md`,
  `docs/p6_5/P6_5_FINAL_VALIDATION_REPORT.md`,
  `docs/p6_5/P7_READINESS_REPORT.md`, BLS fixture/replay tests, temporal and
  revision tests, SQL/PostgreSQL checks, claim/evidence/Show Evidence tests,
  Quant Bridge and learning integration tests, and independent A–K audits.
- Compatibility: additive P6.5 modules preserve P0–P6 contracts. No plugin,
  MCP connector, provider SDK, package, or dynamic execution runtime was
  installed; the capability decision is recorded in `DEPENDENCY_RECORD.md`.
- Review: P6.5 Gate PASS for the bounded local vertical slice; the direct SQL
  writer/source-verified flag and live operational controls remain explicit
  production follow-ups. P7 is waiting for human approval.

## 2026-10-03 — P6.6 strategy research and simulation lab

- Change: added immutable feature definitions/graphs, reviewed strategy specs,
  constrained IR/compiler adapters, educational code/math/finance traces,
  P5/P5.5 backtest routing, frozen OOS/walk-forward metadata, deterministic
  PaperRun replay, comparison/drift diagnostics, LearningCards, safe export,
  and additive strategy-lab persistence tables.
- Reason: make strategy ideas testable and teachable while preserving the
  existing quant execution and provenance authorities.
- Evidence: `docs/p6_6/P6_6_FINAL_VALIDATION_REPORT.md`, A–J independent audits,
  focused P6.6 tests, full 187-pass regression, Ruff/notebook/governance/pip
  checks, and the P6.5 PostgreSQL migration verification.
- Compatibility: additive `finahinking.p6_6` modules and migration 002; no
  new dependency, plugin, broker, provider SDK, or live execution path.
- Review: P6.6 Gate PASS; P7 is READY but remains WAITING FOR HUMAN APPROVAL.

## 2026-10-03 — P7 continuity and community completion audit

- Change: added misconception lifecycle, private timeline, evidence-grounded
  optional guidance, saved workspace references, strategy-version provenance,
  typed community claims/attachments/summaries, an inert prompt/tool/link
  boundary, P6.5 event learning adapter, and room-bound projections.
- Reason: close mission-level gaps found by independent audit rather than
  equating generic CRUD coverage with the P7 product contracts.
- Evidence: 29 P7 tests, 244 passed/1 skipped in both environments, Ruff,
  notebook/governance/pip gates, PostgreSQL schema/index checks, and the exact
  mission-44 gate matrix plus A–J pass register.
- Compatibility: no new runtime dependency or plugin; P4–P6.6 authorities are
  preserved. Legacy projection schemas gain the room-scope column through both
  migration entry points.
- Review: P7 local gate PASS; P8 readiness decision B only, implementation waits
  for human approval and hosted operational controls remain open.

## 2026-10-03 — P7.5 Knowledge Engine and local product

- Change: added a typed, deterministic KnowledgeCatalog with a 15-concept
  Return→Overfitting curriculum, four learning paths, required domain coverage,
  event links, equations, derivations, code/finance/quant/strategy links, and
  source references; added a loopback SQLite/sample local application and E2E
  journeys.
- Reason: make the governed P4–P7 research core usable as an education-first
  product without duplicating P7 personal state or adding cloud/broker scope.
- Evidence: P7.5 unit/local/E2E tests, full regression in both environments,
  P7.5 independent reviews A–J, local sample smoke, diagnostics, and
  `docs/p7_5/P7_5_FINAL_VALIDATION_REPORT.md`.
- Compatibility: no new required dependency; standard-library shell, existing
  P7 SQLite/PostgreSQL contracts, captured BLS fixture, and explicit no-order
  boundary.
- Review: P7.5 Product-Usable Gate PASS; P8 source-beta readiness is conditional
  on maintainer-owned GitHub publication and any selected native package.

## 2026-10-03 — P8 public-beta preparation

- Change: added public README/quickstart/install/tutorials, contribution
  contracts, privacy/security/license/limitations docs, CI/release workflows,
  issue forms, release checks, secret scan, clean-install procedure, and the
  47-item public-beta gate.
- Reason: make the source distribution reproducible and safe to publish while
  keeping hosted accounts, cloud sync, broker credentials, and real-money work
  out of scope.
- Evidence: `docs/p8/P8_FINAL_VALIDATION_REPORT.md` and
  `docs/p8/P8_PUBLIC_BETA_GATE.md`; no Git remote or release tag exists in this
  checkout, so external publication is explicitly conditional.
- Review: stop at P8 gate for human inspection.

## 2026-10-02 — P0 foundation

- Change: established repository governance, role contracts, and phase-gate
  records.
- Reason: make research changes auditable before adding data or factors.
- Evidence: `python scripts/validate_governance.py` and the governance tests.
- Compatibility: no package API or data format changes.
- Review: P0 gate recorded as PASS in `docs/PROJECT_STATE.md`.
