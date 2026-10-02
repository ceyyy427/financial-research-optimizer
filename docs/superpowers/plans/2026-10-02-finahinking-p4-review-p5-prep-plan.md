# Finahinking P4 Review and P5 Preparation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the requested P4 architecture review and prepare a review-only P5 gate without implementing P5.

**Architecture:** Review the existing `ResearchRun`, `ExperimentEngine`, and `RunStore` contracts against the research loop and provenance requirements. Record conclusions and non-critical gaps as documentation, while keeping P4 execution and storage unchanged. Define P5 acceptance boundaries and dependency choices as proposals only.

**Tech Stack:** Markdown, existing Python/Pandas/Pytest/Ruff toolchain, Git.

**Spec:** `/Users/mac/.codex/attachments/cbaaa88f-2ccb-4c13-af30-7f89f14244fc/pasted-text-1.txt`

## Global Constraints

- P0–P4 remain PASS and the repository stops at P4 pending human review.
- Do not implement P5 backtesting, portfolio, risk, or performance features.
- Do not install or introduce P5 dependencies.
- Preserve explicit research limitations, no-advice boundary, and deterministic offline tests.
- Any provenance gap that is not critical is documented as a proposal, not implemented.

## Review Focus

- ResearchRun must preserve the question-to-insight chain; verify every required field is represented.
- Provenance must identify source, retrieval metadata, dataset fingerprint, factor/method configuration, and result fingerprint; document missing version/environment/validation details.
- Reproduction must detect dataset, factor, parameter, and result drift without executing stored code.
- P5 design must define forbidden scope and research-validity controls before implementation.
- Dependency choices must be evaluated without installation.

### Task 1: P4 architecture and provenance review

**Files:**
- Create: `docs/reviews/P4_FINAL_REVIEW.md`
- Create: `docs/reviews/P4_PROVENANCE_IMPROVEMENT_PROPOSAL.md`
- Modify: `ARCHITECTURE.md`

**Interfaces:**
- Consumes: `src/finahinking/experiments/{models,engine,storage}.py` and P4 gate evidence.
- Produces: stable architecture verdict, explicit weaknesses, and deferred provenance requirements.

- [ ] Review the ResearchRun fields and execution path against the required research loop.
- [ ] Record strengths, weaknesses, frozen decisions, remaining risks, future considerations, and the `P4 FOUNDATION STABLE` recommendation.
- [ ] If provenance is incomplete for source version, implementation identity, environment, or validation status, record a non-implementation proposal.
- [ ] Align `ARCHITECTURE.md` with the delivered P4 boundary.

### Task 2: P5 gate design and dependency strategy

**Files:**
- Create: `docs/phases/P5_GATE_DESIGN.md`
- Create: `P5_DEPENDENCY_PLAN.md`

**Interfaces:**
- Consumes: P4 frozen boundary and the requested tentative backtest/evaluation direction.
- Produces: human-reviewable P5 objective, architecture, acceptance/testing/security/research-validity criteria, dependency comparison, and forbidden scope.

- [ ] Define P5 as a future backtest and evaluation phase only; keep all implementation explicitly out of scope now.
- [ ] Define Strategy, Portfolio, Position, Trade, Return, Risk, and Performance Attribution as tentative concepts with required controls.
- [ ] Compare vectorbt and Backtrader for research fit, maintenance, license, integration complexity, and reproducibility.
- [ ] Evaluate Pyfolio Reloaded and the need for additional statistical libraries; record “do not install now.”

### Task 3: Final state hygiene and verification

**Files:**
- Modify: `docs/PROJECT_STATE.md`, `CHANGELOG.md`
- Delete: temporary root-level `Untitled*.ipynb` artifacts created by local notebook checks.

- [ ] Link the new review and P5 design evidence from the authoritative project state.
- [ ] Run governance validation, the full test suite, Ruff, notebook gate, dependency checks, and diff checks.
- [ ] Confirm the worktree is clean and P5 remains unimplemented.

## Completion evidence

The task is complete only when the new review documents exist, the project state says
P0–P4 PASS and waiting for human review, all required verification commands pass,
and no P5 implementation or dependency installation is present.
