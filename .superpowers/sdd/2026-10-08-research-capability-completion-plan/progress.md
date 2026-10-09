# SDD ledger — plan: /Users/mac/.codex/worktrees/research-agent-runtime/Finahinking Autonomous Builder/docs/superpowers/plans/2026-10-08-research-capability-completion-plan.md

## Setup

- Base: `5d0a2cd` (`release(research): complete autonomous research runtime`).
- Scope: continue the approved offline, paper-only research capability expansion without vendor SDKs, broker/order/live execution, secret persistence, or unattended self-modifying code.
- Spec authority read: `docs/PROJECT_STATE.md`, `docs/RESEARCH_RUNTIME_RELEASE_CHECKLIST.md`, `docs/RESEARCH_ENGINE_ADMISSION_CHECKLIST.md`, `docs/RESEARCH_RUNTIME_GUIDE.md`.
- Plan workspace: `.superpowers/sdd/2026-10-08-research-capability-completion-plan/`.

## Pre-flight interface scan

| Task(s) | Shared interface/files | Finding and ruling |
|---|---|---|
| 1 / 17 | release matrix and final report/checklist | T1 produces typed capability statuses; T17 consumes them. Ruling: status names remain explicit and are never collapsed into a percentage. |
| 2 / 3 | provider status/config, provider adapters/drivers | T2 owns user configuration and credential references; T3 consumes only resolved, redacted config. Ruling: values stay outside config and artifacts. |
| 2 / 15–16 | `local_app.py`, provider/data settings routes | T2 may add provider routes; T15–16 extend read-only UI. Ruling: preserve CSRF and allow-list boundaries before UI additions. |
| 3 / 4 | provider contracts and Codex bridge | T3 returns structured contract results; T4 handles external task handoff. Ruling: neither may turn unverified external responses into success. |
| 4 / 13–14 | `job_queue.py`, `workflow.py`, runtime service | T4 adds external task records; T13 composes durable stages; T14 adds limits. Ruling: external handoff remains an explicit terminal/non-terminal state and is limit-accounted. |
| 5 / 6 | factor proposal/pipeline | T5 produces versioned governed hypotheses; T6 consumes them for bounded experiments. Ruling: template DSL stays allow-listed; experiment metadata binds to lineage. |
| 5 / 7 | factor hypothesis/catalog/registry | T5 proposals do not write registry; T7 adds audited admission. Ruling: only explicit human admission can mutate registry. |
| 6 / 9 / 15 | reports and comparison payloads | T6/T9 produce server-side results; T15 renders them. Ruling: browser remains read-only and never recomputes metrics. |
| 7 / 12 | catalog admission and learning policy | T7 governs factor admission; T12 governs next-round learning policies. Ruling: both require explicit admission and preserve fingerprints. |
| 8 / 9 | engine registry and quant analytics | T8 may fall back to deterministic engine; T9 analyzes normalized server results. Ruling: optional engines remain `NOT_INSTALLED`/`DEFERRED` without verified sandbox. |
| 10 / 11 | risk and portfolio/paper runtime | T10 exposes risk gates; T11 consumes only eligible risk results. Ruling: unknown/failed risk blocks rebalance and paper decisions. |
| 11 / 12 | paper ledger and settlement learning | T11 produces paper ledger fingerprints; T12 requires as-of settlement/ledger digests. Ruling: no unsettled or raw provider payload can update policy. |
| 13 / 14 | runtime service, provider/factor limits | T13 orchestrates stages; T14 enforces shared resource ceilings. Ruling: limits fail closed with traceable `RESOURCE_LIMIT`. |
| 15 / 16 | report tree, UI, browser routes | T15 provides schema-versioned read-only payloads; T16 verifies public journeys. Ruling: no browser-side financial computation or secret/path/prompt leakage. |
| 17 | all tasks and release docs | T17 records evidence from every completed task and preserves `OFFLINE_PASS`, `ISOLATED_DEFERRED`, `EXTERNAL_UNVERIFIED`, `NOT_IN_SCOPE`. |

## Task self-consistency scan

| Task | Test/code/doc agreement |
|---|---|
| 1 | Matrix fields and named statuses match the stated test cases; no conflict found. |
| 2 | Store, route, and redaction tests cover the produced interfaces; no conflict found. |
| 3 | Adapter result contract matches failure/retry tests; no conflict found. |
| 4 | Dispatch record and handoff states match idempotency/fingerprint tests; no conflict found. |
| 5 | Registry DSL interfaces match factor template tests; no conflict found. |
| 6 | Experiment result fields match ranking/decay tests; no conflict found. |
| 7 | Audited loader and explicit admission match registry tests; no conflict found. |
| 8 | Engine resolution statuses match fallback tests and admission checklist; no conflict found. |
| 9 | Analytics outputs match surface/performance test inputs; no conflict found. |
| 10 | Exposure/stress interfaces match risk blocking tests; no conflict found. |
| 11 | Optimizer/rebalance interfaces match paper-only constraint tests; no conflict found. |
| 12 | Proposal persistence/apply interfaces match approval/as-of tests; no conflict found. |
| 13 | Runtime service methods match queue/checkpoint/cancel tests; no conflict found. |
| 14 | Runtime limits and metrics match quota tests; no conflict found. |
| 15 | Report/UI payload additions match schema and frontend tests; no conflict found. |
| 16 | Browser routes and docs match stated E2E checks; no conflict found. |
| 17 | Final report categories and gate commands match release requirements; no conflict found. |

Pre-flight ruling: the plan is internally consistent and can proceed task-by-task. Any implementation ambiguity will be recorded as a task-specific `Ruling:` before continuing.

Task 1 review: PASS WITH MINOR FOLLOW-UP — source-path and checklist-marker drift is now fail-closed; numeric test-stat parsing and a direct mapping-proxy mutation assertion remain minor follow-up items, not release blockers. The per-task report is retained as plan traceability.
Task 1: complete (commits 5d0a2cd..c7fd749, tests: python3 -m pytest tests/research/test_release_matrix.py tests/research/test_engine_registry.py tests/research/test_capability_vertical_slice.py -q → 18 passed in 0.73s)

Task 2: fix round 1/5 (1 addressed, 2 minor follow-ups — reserved/private DNS endpoint hosts were rejected fail-closed; persistence/keychain coverage and explicit capability projection remain minor; commits 1056da0..bf7aa71).
Task 2 review: PASS WITH MINOR FOLLOW-UP — credential references, redaction, CSRF, allow-lists, atomic restart storage, and endpoint boundary are approved; remaining persistence/keychain and capability-projection coverage is non-blocking.
Task 2: complete (commits c7fd749..bf7aa71, tests: python3 -m pytest tests/research/test_provider_config.py tests/research/test_provider_status.py tests/research/test_credentials.py tests/research/test_provider_adapters.py tests/research/test_ui.py tests/p7_5/test_local_app.py -q → 79 passed in 1.24s)
Task 3: complete (commits bf7aa71..2df8db5, tests: python3 -m pytest tests/research/test_provider_adapters.py tests/research/test_provider_live_contract.py -q → 25 passed in 0.56s)
Task 4: fix round 1/5 (2 addressed, 0 open; external jobs excluded from normal workers and callback state persisted durably; commits cd0b690..937ab0e).
Task 4: fix round 2/5 (1 addressed, 0 open; legacy external rows backfilled and normalized on queue initialization; commits 937ab0e..f196938).
Task 4 review: PASS after two fix rounds; focused re-review found no open findings. Full suite had a transient/pre-existing wheel probe failure in the implementer run; it is outside the changed dispatch paths and must be rechecked at the final gate.
Task 4: complete (commits 2df8db5..f196938, tests: python3 -m pytest tests/research/test_codex_dispatch.py tests/research/test_codex_bridge.py tests/research/test_job_queue.py tests/research/test_workflow.py tests/research/test_vertical_slice.py -q → 44 passed in 0.65s)
Task 5: fix round 1/5 (4 addressed, 0 open; template provenance/version binding, registry injection, alias resolution, and registration validation corrected; commits e7ad63e..5ad2d7f).
Task 5 review: PASS after scoped re-review; no new breakage found. First task-done invocation had a quoted glob and ran no tests; rerun with shell expansion passed 93 tests and recorded completion.
Task 5: complete (commits f196938..5ad2d7f, tests: python3 -m pytest tests/research/test_factor_template_catalog.py tests/factors tests/research/test_factor_*.py -q → 93 passed in 1.34s)
Task 6: fix round 1/5 (3 addressed, 0 open; deterministic unordered axes, safe key normalization, finite budget/grid/split validation; commits 4106d43..9efa5ed).
Task 6 review: PASS after scoped re-review; no new breakage found. Implementer full suite again saw the existing wheel probe failure; final gate must rerun it.
Task 6: complete (commits 5ad2d7f..9efa5ed, tests: python3 -m pytest -q tests/research/test_factor_experiments.py tests/research/test_factor_pipeline.py tests/research/test_reports.py → 18 passed in 1.02s)
Task 7: fix round 1/5 (3 addressed, 0 open; evaluation fingerprint binding, paper-only eligibility, and source lineage preservation; commits 3c8861f..6954b9f).
Task 7: fix round 2/5 (1 addressed, 0 open; missing evaluation fingerprints now fail closed at loader/admission; commits 6954b9f..729f157).
Task 7 review: PASS after two fix rounds; lower-level permissive legacy audit remains intentional backward compatibility and is not used by strict catalog loading.
Task 7: complete (commits 9efa5ed..729f157, tests: python3 -m pytest -q tests/research/test_factor_catalog_loader.py tests/research/test_factor_catalog.py tests/research/test_factor_registry.py → 30 passed in 0.50s)
Task 8: fix round 1/5 (5 addressed, 2 open at first re-review; evidence-gated availability, killable timeout contract, redaction, authoritative provenance, sweep binding, and frozen snapshot; commits cb96b60..f5367ba).
Task 8: fix round 2/5 (2 addressed, 0 open; finite timeout and separate engine/runtime version evidence; commits f5367ba..aa03b65).
Task 8 review: PASS after two fix rounds; optional engines remain DEFERRED unless the external evidence/verifier/termination contract is present. Wheel probe remains a final-gate item.
Task 8: complete (commits 729f157..aa03b65, tests: python3 -m pytest -q tests/research/test_optional_engine_admission.py tests/research/test_engine_registry.py tests/research/test_workflow.py → 32 passed in 0.68s)
Task 9: fix round 1/5 (5 addressed, 0 open; robustness flags, ledger period aggregation, invalid costs, missing-equity gaps, benchmark returns, and dedicated tests; final amended commit cbfab6d).
Task 9 review: PASS after corrected amended-range re-review; implementer reports Ruff unavailable in its environment, to be rechecked at final gate.
Task 9: complete (commits aa03b65..cbfab6d, tests: python3 -m pytest -q tests/research/test_quant_analytics.py tests/research/test_reports.py → 8 passed in 0.51s)
Task 10: fix round 1/5 (7 addressed, 0 original open; strict canonical status/fingerprint, safe evidence, per-record PIT, liquidity/stress validation, malformed input, deep immutability; commits 0b10be9..7aded53).
Task 10: fix round 2/5 (2 addressed; secret-safe identifiers/direct constructors and nonempty evidence; commits 7aded53..7eaf59e).
Task 10: fix round 3/5 (nested scenario values addressed; adjacent key issue surfaced; commits 7eaf59e..a34505a).
Task 10: fix round 4/5 (nested scenario keys addressed, 0 open; commits a34505a..dedd7c6).
Task 10 review: APPROVED at dedd7c6; all findings addressed. Full suite varies only at existing wheel probe; final gate must retain diagnostics. Ruff not available to implementer/reviewer and remains a final-gate item.
Task 10: complete (commits cbfab6d..dedd7c6, tests: python3 -m pytest -q tests/research/test_risk_exposures.py tests/research/test_risk_runtime.py tests/research/test_portfolio_runtime.py tests/research/test_paper_trader.py tests/research/test_autonomous_runtime_vertical_slice.py → 38 passed in 0.74s)
Task 4: complete (commits 2df8db5..f196938, tests: python3 -m pytest tests/research/test_codex_dispatch.py tests/research/test_codex_bridge.py tests/research/test_job_queue.py tests/research/test_workflow.py tests/research/test_vertical_slice.py -q → 44 passed in 0.65s)
Task 5: complete (commits f196938..5ad2d7f, tests: python3 -m pytest tests/research/test_factor_template_catalog.py tests/factors tests/research/test_factor_catalog.py tests/research/test_factor_dsl.py tests/research/test_factor_evaluation.py tests/research/test_factor_loop.py tests/research/test_factor_pipeline.py tests/research/test_factor_proposals.py tests/research/test_factor_registry.py tests/research/test_factor_template_catalog.py -q → 93 passed in 1.34s)
Task 6: complete (commits 5ad2d7f..9efa5ed, tests: python3 -m pytest -q tests/research/test_factor_experiments.py tests/research/test_factor_pipeline.py tests/research/test_reports.py → 18 passed in 1.02s)
Task 7: complete (commits 9efa5ed..729f157, tests: python3 -m pytest -q tests/research/test_factor_catalog_loader.py tests/research/test_factor_catalog.py tests/research/test_factor_registry.py → 30 passed in 0.50s)
Task 8: complete (commits 729f157..aa03b65, tests: python3 -m pytest -q tests/research/test_optional_engine_admission.py tests/research/test_engine_registry.py tests/research/test_workflow.py → 32 passed in 0.68s)
Task 9: complete (commits aa03b65..cbfab6d, tests: python3 -m pytest -q tests/research/test_quant_analytics.py tests/research/test_reports.py → 8 passed in 0.51s)
Task 10: complete (commits cbfab6d..dedd7c6, tests: python3 -m pytest -q tests/research/test_risk_exposures.py tests/research/test_risk_runtime.py tests/research/test_portfolio_runtime.py tests/research/test_paper_trader.py tests/research/test_autonomous_runtime_vertical_slice.py → 38 passed in 0.74s)
Task 11: complete (commits dedd7c6..2b9d0f1, tests: python3 -m pytest -q tests/research/test_portfolio_optimizer.py tests/research/test_portfolio_runtime.py tests/research/test_paper_trader.py tests/research/test_risk_runtime.py → 23 passed in 0.53s)
Task 12: fix round 1/5 (4 addressed, 0 open; enrichment retries, canonical proposal digest, deep immutability, exact nested schema and secret/path safety; commits a269836..9b9e714).
Task 12: follow-up review PASS at 5eee2c5; preview-only enrichment retry preserves the stored approval. Focused review 44 passed. Larger research suite reported a DATA_UNAVAILABLE vertical-slice failure; root-cause investigation is required before release.
Task 12: complete (commits 2b9d0f1..5eee2c5, tests: python3 -m pytest -q tests/research/test_learning_application.py tests/research/test_learning_manager.py tests/research/test_run_store.py tests/research/test_contracts.py → 50 passed in 0.56s)
Task 13: fix round 1/5 (1 addressed, 0 open; scoped runtime execution to the requested job so concurrent queued jobs cannot be returned as the wrong terminal result; commits 9013568..f3924c1). Re-review PASS, 24 focused tests.
Task 13: complete (commits 5eee2c5..f3924c1, tests: python3 -m pytest -q tests/research/test_runtime_service.py tests/research/test_job_queue.py tests/research/test_worker.py → 24 passed in 1.19s)
Task 14: fix round 1/5 (1 addressed, 0 open; isolated per-run RuntimeBudget/metrics and fixed cancellation initialization under concurrent runs; commits 46237c3..332428f). Scoped re-review PASS; focused 42 passed with existing multiprocessing warnings.
Task 14: complete (commits f3924c1..332428f, tests: python3 -m pytest -q tests/research/test_runtime_limits.py tests/research/test_runtime_service.py tests/research/test_provider_adapters.py tests/research/test_factor_pipeline.py tests/research/test_factor_experiments.py → 42 passed, 3 warnings in 1.29s)
Task 15: fix round 1/5 (4 addressed, 0 open; corrected active-stage precedence, blocked data-state mapping, report route links, and frontend schema preservation; commits 3b03222..e9c7b77). Scoped re-review PASS; 28 Python and 15 Node focused tests passed. Minor dead selector remains deferred.
Task 15: complete (commits 332428f..e9c7b77, review clean except 1 deferred minor)
Task 16: fix round 1/5 (2 addressed, 0 open; portable Playwright browser discovery/explicit skip and deterministic evidence manifest excluding self-entry; commits 28bd0b1..44acec9). Scoped re-review PASS; 3 tests passed and 1 environment skip, with prior 4-test Chromium evidence and seven verified artifacts retained.
Task 16: complete (commits e9c7b77..44acec9, review clean)
Task 17: complete (commits 44acec9..db4f4ed, conditional release report; focused gates and local browser evidence documented; full pytest remains 921 passed, 2 failed, 2 skipped; the known concurrency/DNS fixture blockers remain explicitly retained)
Task 17 follow-up: Ruff gate is clean at `dabe0a2` (`python3 -m ruff check src tests scripts` → exit 0); vertical-slice `DATA_UNAVAILABLE` and concurrent-runtime `RESOURCE_LIMIT` remain unresolved and prevent a full release claim.
Task 14: complete (commits f3924c1..332428f, tests: python3 -m pytest -q tests/research/test_runtime_limits.py tests/research/test_runtime_service.py tests/research/test_provider_adapters.py tests/research/test_factor_pipeline.py tests/research/test_factor_experiments.py → 42 passed, 3 warnings in 1.29s)
