# Finahinking P4.5 Research OS Validation Audit Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the frozen P4 Research OS foundation and document its readiness for human-approved P5 design without implementing P5.

**Architecture:** Audit the existing repository, P4 domain model, experiment lifecycle, provenance, quantitative safeguards, user workflow, and future extension seams using current source and test evidence. Update only the governance phase parser needed to represent the explicit P4.5 validation phase; leave P4 experiment code and frozen architecture unchanged.

**Tech Stack:** Markdown, Python 3.11+ (verified runtime 3.13.7), Pandas/NumPy, pytest, Ruff, Jupyter/nbconvert, pip, Git, and repository search tools.

**Spec:** `/Users/mac/.codex/attachments/e260dce5-b94a-48ee-babb-c2ee95642c12/pasted-text-1.txt`

## Audit scope

The audit covers repository/module structure, ResearchRun semantics, experiment
lifecycle, data provenance, quantitative validity, the user research journey,
P5 compatibility, P6 knowledge readiness, future agent/MCP seams, and current
dependencies. It excludes P5/P6/P7 implementation and any dependency install.

## Audit objectives

- Prove whether P4 is a stable Research OS foundation.
- Confirm research results are reproducible and traceable.
- Confirm built-in quantitative logic is appropriately aligned and limited.
- Demonstrate the end-to-end human research journey.
- Identify non-blocking gaps that future phases must address.
- Decide PASS or NEEDS IMPROVEMENT using repository evidence.

## Audit questions

- Are module/domain/documentation boundaries maintainable and extensible?
- Can ResearchRun explain intent, method, evidence, and learning?
- Does the lifecycle behave deterministically and fail safely?
- Can a result be traced back to source, data, factor, and configuration?
- Are look-ahead, leakage, factor meaning, IC, and coverage handled honestly?
- Can P5/P6/P7 attach without weakening the frozen P4 invariants?
- Are forbidden dependencies and integrations absent from the project?

## Tools used

Git (`git ls-files`, status, diff), `find`, `rg`, Python, pytest, Ruff,
Jupyter/nbconvert, pip metadata/checks, Homebrew package inspection for libomp,
and structured Markdown/file operations. Computer Use is not used.

## Expected evidence

- Source and module maps linked to concrete files.
- Named tests for normal, failure, and edge cases.
- Fresh full-suite, lint, notebook, governance, and dependency outputs.
- A deterministic volatility-question ResearchRun round-trip/reproduction.
- Required audit documents with explicit findings and decisions.
- An independent review covering architecture, correctness, security,
  maintainability, and research validity.

## Global Constraints

- Do not implement P5, add a Backtest Engine, install P5 dependencies, or install Ollama.
- Do not modify the frozen P4 architecture unless a critical issue is discovered.
- Use existing tests and notebook execution as evidence; do not create fake validation.
- Preserve the research-laboratory identity, human judgment, no-advice boundary, and deterministic offline defaults.
- The final decision must be either `PASS` or `NEEDS IMPROVEMENT`; if PASS, P5 remains waiting for human approval.

## Review Focus

- Architecture boundaries must remain separated and extensible to P5/P6/P7 without P5 implementation.
- ResearchRun must answer what was asked, how it was tested, what evidence was produced, and what was learned.
- Provenance claims must distinguish actual replay/drift behavior from deferred source-version and implementation-identity gaps.
- Quantitative validation must cover shift, horizon, IC, coverage, constant inputs, and documented limitations.
- Dependency and future-agent audits must prove absence of forbidden packages, imports, or tools.

### Task 1: Represent the P4.5 validation phase safely

**Files:**
- Test: `tests/validation/test_governance.py`
- Modify: `scripts/validate_governance.py`
- Modify: `docs/PROJECT_STATE.md`

- [x] Add a failing regression test showing a valid `Current phase: P4.5 Research OS Validation` state is accepted.
- [x] Run the targeted test and observe the expected phase-validation failure.
- [x] Extend only the phase parser/allowed set to accept `P4.5`; preserve P0–P4 checks and P5 rejection.
- [x] Run the targeted test and then the full governance test file.
- [x] Set the authoritative state to P4.5 Research OS Validation, P0–P4 PASS, and P5 human approval pending.

### Task 2: Produce architecture, domain, lifecycle, provenance, and quant audits

**Files:**
- Create: `docs/reviews/P4_5_ARCHITECTURE_AUDIT.md`
- Create: `docs/reviews/P4_5_RESEARCHRUN_AUDIT.md`
- Create: `docs/reviews/P4_5_EXPERIMENT_AUDIT.md`
- Create: `docs/reviews/P4_5_PROVENANCE_AUDIT.md`

- [x] Use `git ls-files`, `find`, `rg`, source inspection, and tests to document repository boundaries and extension points.
- [x] Verify every ResearchRun field and answer the four user-facing research questions.
- [x] Trace creation/configuration/execution/validation/storage/insight and record deterministic and failure behavior.
- [x] Trace source -> dataset -> dataset version metadata -> factor -> experiment -> result -> insight, including known deferred gaps.

### Task 3: Produce research and future-readiness audits

**Files:**
- Create: `fixtures/p4_5/volatility_workflow.csv`
- Create: `tests/experiments/test_p4_5_workflow.py`
- Create: `docs/reviews/P4_5_QUANT_VALIDATION.md`
- Create: `docs/reviews/P4_5_USER_WORKFLOW_AUDIT.md`
- Create: `docs/reviews/P5_COMPATIBILITY_AUDIT.md`
- Create: `docs/reviews/P6_READINESS_AUDIT.md`
- Create: `docs/reviews/AGENT_READINESS_AUDIT.md`
- Create: `docs/reviews/DEPENDENCY_AUDIT.md`

- [x] Validate look-ahead, leakage, factor meaning, shift, horizon, IC, coverage, and edge cases against code/tests/notebook evidence.
- [x] Walk through “Does volatility predict future returns?” without implementing a volatility predictor.
- [x] Preserve that workflow as a deterministic fixture/test so its fingerprints and round-trip are independently reproducible.
- [x] Describe how future P5 artifacts become ResearchRun evidence and insight while preserving frozen P4 contracts.
- [x] Assess ResearchRun as a foundation for a personal research graph and future knowledge engine.
- [x] Assess future Research Agent/MCP tool seams only; do not implement agents or install Ollama.
- [x] Verify the current environment and absence of vectorbt, Backtrader, Pyfolio Reloaded, and Ollama.

### Task 4: Final P4.5 report and independent review

**Files:**
- Create: `docs/reviews/P4_5_FINAL_VALIDATION_REPORT.md`

- [x] Summarize architecture, ResearchRun, experiment, provenance, quantitative, workflow, P5, P6, agent, and dependency results.
- [x] Record a single final decision and recommendation.
- [x] Run governance validation, all tests, Ruff, notebook gate, pip check, document audit, dependency absence checks, and diff checks.
- [x] Request independent architecture/correctness/security/research-validity review.
- [x] Commit only documentation and the minimal governance parser/test change; confirm clean worktree and stop at P4.5.

## Pass criteria

P4.5 passes only if all required audit documents exist, the existing test and
notebook evidence is green, the validator accepts the declared P4.5 phase while
still rejecting P5, no forbidden project dependency/import/integration appears,
and the independent review finds no Critical or Important issue.
