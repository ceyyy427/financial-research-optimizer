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

## 2026-10-02 — P0 foundation

- Change: established repository governance, role contracts, and phase-gate
  records.
- Reason: make research changes auditable before adding data or factors.
- Evidence: `python scripts/validate_governance.py` and the governance tests.
- Compatibility: no package API or data format changes.
- Review: P0 gate recorded as PASS in `docs/PROJECT_STATE.md`.
