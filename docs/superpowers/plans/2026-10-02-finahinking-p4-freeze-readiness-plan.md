# Finahinking P4 Freeze and P5 Readiness Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the delivered P4 foundation and document whether the architecture is ready for human-approved P5 design work without implementing P5.

**Architecture:** Describe the existing `ResearchRun -> ExperimentEngine -> RunStore` boundary, its lineage and fingerprint contracts, and its future extension seams. Keep all P5 concepts at the design/documentation boundary and reuse the already-reviewed dependency evaluation rather than installing packages.

**Tech Stack:** Markdown, existing Python/Pandas/Pytest/Ruff/Jupyter environment, Git.

**Spec:** `/Users/mac/.codex/attachments/116697eb-dc57-43a7-b6ed-fe140322f08f/pasted-text-1.txt`

## Global Constraints

- Do NOT implement P5.
- Do not install any new dependencies; vectorbt, Backtrader, and Pyfolio Reloaded remain uninstalled until P5 approval.
- P0–P4 remain PASS and the current phase is P4 Architecture Freeze.
- Preserve the research-laboratory philosophy, no-advice boundary, and deterministic offline verification.
- Stop after the review and final report; the next action is P5 human approval.

## Review Focus

- Every required ResearchRun field must be represented and explained as part of the research loop.
- Lifecycle and lineage documentation must identify where validation, fingerprints, and storage occur.
- Drift claims must match the actual P4 implementation, including replay-only parameter comparison.
- P5 readiness must connect future strategy/portfolio/trade/risk objects back to ResearchRun without implementing them.
- Candidate dependency claims must remain evaluation-only and license/maintenance caveats must be explicit.

### Task 1: Freeze the P4 architecture

**Files:**
- Create: `docs/architecture/P4_ARCHITECTURE_FREEZE.md`

**Interfaces:**
- Consumes: `src/finahinking/experiments/{models,engine,storage}.py`, `ARCHITECTURE.md`, and P4 review evidence.
- Produces: the frozen ResearchRun domain model, lifecycle, lineage, fingerprint strategy, local storage decision, and P5/P6/P7 extension points.

- [ ] Document Question, Hypothesis, Dataset, Factor, Method, Parameters, Result, Conclusion, Insight, and Limitations and explain why ResearchRun is the core object.
- [ ] Document creation through insight generation and identify validation and persistence boundaries.
- [ ] Document dataset/factor/experiment/result lineage and the answer path for “Where did this result come from?”.
- [ ] Document dataset/result fingerprints and precise drift behavior without promising unimplemented candidate-parameter comparison.
- [ ] Explain why local JSON RunStore is sufficient for P4 and list PostgreSQL, Research Graph, and Knowledge Engine as future migrations only.
- [ ] Describe P5 Backtest & Evaluation, P6 Knowledge Engine, and P7 Agent Evolution System as extension points only.

### Task 2: Review P4 philosophy and P5 readiness

**Files:**
- Create: `docs/reviews/P4_PHILOSOPHY_REVIEW.md`
- Create: `docs/reviews/P5_READINESS_REVIEW.md`
- Create: `docs/P5_DEPENDENCY_DECISION.md`

**Interfaces:**
- Consumes: the P4 freeze document, existing P4 final review, P5 gate design, and dependency plan.
- Produces: explicit strengths, weaknesses, future risks, P5 object mapping, research-integrity controls, candidate evaluation, and accepted/rejected dependency decisions.

- [ ] Decide whether P4 preserves Question -> Experiment -> Evidence -> Insight, and document strengths, weaknesses, and future risks.
- [ ] Assess how Strategy, Portfolio, Position, Trade, Order, Return, Risk, and Performance Attribution should connect to ResearchRun in a future P5.
- [ ] Require transaction costs, slippage, benchmark, survivorship bias, look-ahead bias, leakage, and corporate-action policy before P5 implementation.
- [ ] Evaluate vectorbt, Backtrader, and Pyfolio Reloaded by purpose, license, maintenance, architecture fit, and risks without installing them.
- [ ] State candidate, rejected, and deferred dependency decisions clearly.

### Task 3: Update state, report, and verify

**Files:**
- Create: `docs/P4_FREEZE_COMPLETION_REPORT.md`
- Modify: `docs/PROJECT_STATE.md`

- [ ] Set the authoritative phase to `P4 Architecture Freeze`, retain P0–P4 PASS, and set next action to P5 Human Approval.
- [ ] Report documents created, frozen decisions, P4 stability, P5 readiness, dependency evaluation, risks, and recommendations.
- [ ] Run governance validation, the full tests, Ruff, notebook gate, pip check, diff checks, and document-marker audit.
- [ ] Confirm no P5 imports/source implementation, no dependency manifest changes, and a clean worktree.

## Completion evidence

The task is complete only when all five named deliverables exist, the state file
matches the requested P4 Architecture Freeze status, all verification commands
pass, no new dependency is installed, and the repository stops awaiting human
approval for P5.
