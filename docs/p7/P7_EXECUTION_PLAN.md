# P6.6 Final Validation and P7 Implementation Plan

> **For agentic workers:** Use test-driven implementation with independently
> reviewed task gates. Never start P7 product implementation before Stage A PASS.

**Goal:** Validate and repair the advanced P6.6 mainline, then deliver private
personal intelligence and an explicitly projected evidence-driven community.

**Architecture:** Extend frozen P4–P6.6 domain authorities and the existing
relational persistence path. P7A personal state and P7B community remain separate,
joined only by authorized, sanitized, versioned projection.

**Tech Stack:** Python, existing pandas/NumPy, stdlib SQLite/JSON/cryptography,
existing pytest/Ruff/Jupyter, PostgreSQL migration verification.

**Spec:** `docs/p7/P7_ARCHITECTURE.md`; full user mission is the pasted attachment
`dd4527b2-53f8-4b90-ba6b-af639d5eff7f/pasted-text-1.txt` (89 sections).

## Global constraints

- Starting P6.6 implementation commit: `0bde5fa`; actual starting HEAD: `109e284`.
- Preserve P4–P6.6 historical evidence; earlier P3 stop is superseded by this mission.
- No real-money execution, broker SDK/plugin, copying strategy or investment advice.
- No capability gap = no installation. No default Neo4j, pgvector or agent framework.
- Fixed parameterized SQL; relational ownership and privacy; private by default.
- Truth/provenance/quantitative results cannot be personalized.
- Community content is untrusted data and cannot grant agent/tool authority.
- P8 waits for the next human architectural decision.

## Review focus

- A forged principal or object ID must not allow cross-user read/write/context access.
- Revoked projections attached to old posts must stop access, while private source survives.
- A mismatched strategy feature/config must not silently execute a different plan.
- Repeated encounters and imported comments must not fabricate mastery or factual truth.
- A changed/deleted private artifact must not leave stale public content or orphan references.

## Stage A — P6.6 final validation and repair

### Task A1: Establish current requirements and gate evidence

Files: P6.6 source/tests/contracts, migration scripts, this plan and capability matrix.
Interfaces: existing StrategySpec/IR, FeatureRegistry, StrategyResearchLab, QuantRun,
ResearchRun, PaperRun; output is reproduced defects and baseline command evidence.

- [x] Inspect current HEAD, cleanliness, architectures, skills, tools and environments.
- [x] Reproduce spec/IR/execution, parameter, feature, education and paper mismatches.
- [x] Independently inspect privacy/security/provenance/fingerprint assumptions.

### Task A2: Repair contract mismatches under TDD

Files: `src/finahinking/p6_6/{features,compiler,backtest,education,lab,paper}.py`,
additive P5.5 seams only where needed; `tests/p6_6/` regression tests.
Interfaces: reviewed specs/feature versions → exact constrained execution plan;
historical and paper outputs must identify the same versions/configuration.

- [x] Add failing behavioral tests for every reproduced mismatch; observe RED.
- [x] Fix the root cause with one shared validated plan; do not weaken validation.
- [x] Verify focused tests, complete suites and independent validity/security review.
- [x] Commit repaired P6.6 baseline with relevant gate documentation.

### Task A3: Post-commit P6.6 gate

- [x] Run full `.venv` and `.venv-quant` tests, Ruff, notebook, governance, both pip checks.
- [x] Run PostgreSQL migration gate (including migration 002), shell syntax and diff check.
- [x] Exercise complete strategy, feature, OOS, paper and export journeys.
- [x] Prove fresh QuantRun/ResearchRun provenance.code_commit == HEAD and stable replay.
- [x] Confirm clean worktree; record exact evidence and independent gate decision.

## Stage B — P7 implementation (unlocks only after A3)

### Task B1: Shared identity, permissions and relational foundation

Files: `migrations/003_p7_personal_community.sql`, `src/finahinking/p7/{models,identity,repository}.py`,
existing `p6_5/repository.py` migration sequence, `tests/p7/test_identity_repository.py`.
Interfaces: authenticated session → owner-scoped repository operations and typed
immutable artifact references; no arbitrary owner-ID authorization.

- [x] Write failing tests for auth, ownership, duplicates, FK integrity and injection.
- [x] Add parameterized persistence on the same connection/migration architecture.
- [x] Verify SQLite and PostgreSQL constraints, restarts and transaction rollback.
- [x] Review and commit this independently testable foundation.

### Task B2: Private continuity and explainable learning

Files: `src/finahinking/p7/{personal,mastery,context}.py`, `tests/p7/test_personal.py`.
Interfaces: canonical artifact references + existing P6 learning records → typed
private graph, evidence-derived mastery, misconception continuity, learning threads,
saved workspace, research/strategy history, timeline and bounded context/guidance.

- [x] Write failing tests for all private objects, state derivation and relevant recall.
- [x] Implement explicit evidence and references; reuse existing authority objects.
- [x] Test user B denial, truth immutability, empty/repeated evidence and stale references.
- [x] Verify owner-authorized export/deletion and no broad personal profiling.
- [x] Review and commit private continuity.

### Task B3: Explicit projection and evidence-driven community

Files: `src/finahinking/p7/{projection,community}.py`, `tests/p7/test_community.py`.
Interfaces: selected private artifact + explicit visibility/fields → immutable
sanitized projection; room membership → posts/comments/typed evidence attachments.

- [x] Write failing tests for projection field leaks, consent, membership and revocation.
- [x] Implement versioned copies preserving mandatory provenance/limitations/claim labels.
- [x] Test cross-user attachment bypass, malicious links, prompt injection and SQL attacks.
- [x] Implement attributed summaries, transparent quality indicators and explicit save-as-question.
- [x] Review and commit community/projection.

### Task B4: Complete product journeys and user control

Files: `src/finahinking/p7/{workflows,product}.py`, `tests/p7/test_vertical_slices.py`,
repository-native runnable demo/CLI and deterministic fixtures.
Interfaces: P6.6 momentum/OOS/turnover research and P6.5 real CPI event → persistent
personal journey → sanitized room projection → counter-evidence → private question.

- [x] Write failing end-to-end tests using real existing artifacts and a real repository.
- [x] Implement Personal Home, graph/thread/timeline, sharing preview/revoke and room flow.
- [x] Verify UI/product progressive disclosure and authorization on actual interactions.
- [x] Evaluate continuity, grounded learning, privacy, evidence quality and user control.
- [x] Review and commit complete journeys.

### Task B5: Independent passes A–J and full completion audit

Files: all required `docs/p7/P7_*.md`, `P8_READINESS_REPORT.md`, PROJECT_STATE,
EVOLUTION_LOG, gate commands and requirement-to-evidence matrix.

- [x] Independently audit architecture, personal data, mastery, personalization,
  community, privacy, security, research integrity, learning integrity and reproduction.
- [x] Resolve every material finding via reproduction → RED → minimal fix → full tests.
- [x] Inspect evidence for each mission section and each of the 44 P7 gate items.
- [x] Commit final docs/state, then rerun all post-commit gates and provenance assertions.
- [x] Confirm clean worktree; report P8 A/B/C readiness honestly; do not implement P8.

## Validation commands

Use both `.venv/bin/python -m pytest -q` and `.venv-quant/bin/python -m pytest -q`;
`.venv/bin/ruff check src tests scripts`; `make p1-gate`; both `pip check` commands;
`python scripts/validate_governance.py .`; PostgreSQL migration gate;
`bash -n scripts/verify_p6_5_postgres.sh`; `git diff --check`; `git status --short`.
Journey/provenance validation must run from committed HEAD, not a pre-commit artifact.

## Scope coverage

Mission 0–18/74–75: staged authority, capability/skill/dependency/process policy.
19–33/54–66: identity, relational private graph, evidence mastery, misconception,
threads/history/timeline/workspace/context, export/deletion and product surfaces.
34–53/67/71/76–81: room/community, typed attachments, projection/versioning,
revocation, moderation, quality, summaries and explicit research loops.
68–70/72: two real end-to-end journeys and experimental learning evaluation.
82–88: named documents, independent A–J passes, full gates and final readiness report.
89: human-controlled, privacy-preserving evidence-first loop across all tasks.
