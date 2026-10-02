# Evolution Log

## 2026-10-02 — P4 experiment engine

- Added deterministic ResearchRun, ExperimentEngine, and local RunStore.
- Added canonical JSON and dataset/result fingerprints for reproduction.
- Added no dependency; recorded the decision in DEPENDENCY_PROPOSAL.md.
- Stopped at P4 for human review as required.

Record material architecture and governance changes here. Each entry should
state the date, change, reason, evidence, compatibility impact, and review
result. Small documentation corrections may be grouped in one entry.

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

## 2026-10-02 — P0 foundation

- Change: established repository governance, role contracts, and phase-gate
  records.
- Reason: make research changes auditable before adding data or factors.
- Evidence: `python scripts/validate_governance.py` and the governance tests.
- Compatibility: no package API or data format changes.
- Review: P0 gate recorded as PASS in `docs/PROJECT_STATE.md`.
