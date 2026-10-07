# Task 1 report: full agent role runtime

## Result

Implemented the provider-neutral, paper-only agent role contract and bounded
runtime for analyst, manager, risk, portfolio, paper-trading, and learning
roles. `AgentTask` and `AgentOutcome` are immutable JSON-safe contracts with
input/output digests, typed status/failure, evidence references, and a
paper-only marker. `RoleCapabilityPolicy` allowlists role inputs and exposes
deterministic gateways only to risk, portfolio, and paper roles. `AgentRuntime`
normalizes driver, timeout, duplicate-role, missing-required-role, capability,
provider, and validation failures; removes raw exception messages; and sorts
outcomes by `(role, task_id)`.

Existing `AnalystPool` and `ResearchManager` behavior remains compatible. The
package exports the new contracts and runtime through `finahinking.research`.

## Commit

`<commit>` — `feat(research): add full agent role runtime`

## Verification

- `PYTHONPATH=src python3 -m pytest -q tests/research/test_agent_roles.py tests/research/test_analyst_runtime.py` — 17 passed.
- `python3 -m ruff check src/finahinking/research/agent_roles.py src/finahinking/research/contracts.py src/finahinking/research/__init__.py tests/research/test_agent_roles.py` — passed.
- `PYTHONPATH=src python3 -m compileall -q src/finahinking/research/agent_roles.py src/finahinking/research/contracts.py` — passed.
- Initial TDD RED was observed: focused collection failed with `ModuleNotFoundError` for the not-yet-created `agent_roles` module.

## Risks and unfinished items

- The runtime intentionally returns typed failure envelopes rather than
  retrying or persisting jobs; durable queue/worker behavior belongs to Task 5.
- Deterministic gateways are passed as opaque, allowlisted context values and
  are not serialized by the contracts. Their concrete risk/portfolio/paper
  implementations belong to Task 4.
- A full `tests/research` collection in this shared worktree still reports
  missing Task 2/3 modules while those tasks are in progress; those files were
  not modified by Task 1.
