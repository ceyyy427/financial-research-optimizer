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

`21a960f` — `feat(research): add full agent role runtime`

Hardening follow-up: `8fe8bf7` — `fix(research): harden agent role boundaries`.

Residual boundary follow-up: `08b6c14` — `fix(research): close residual agent boundary gaps`.

Identifier boundary follow-up: `eaa43ad` — `fix(research): seal residual identifier boundaries`.

## Verification

- `PYTHONPATH=src python3 -m pytest -q tests/research/test_agent_roles.py tests/research/test_analyst_runtime.py` — 26 passed.
- `PYTHONPATH=src python3 -m pytest -q tests/research` — 260 passed.
- `python3 -m ruff check src/finahinking/research/agent_roles.py src/finahinking/research/contracts.py src/finahinking/research/__init__.py tests/research/test_agent_roles.py` — passed.
- `PYTHONPATH=src python3 -m compileall -q src/finahinking/research/agent_roles.py src/finahinking/research/contracts.py` — passed.
- Initial TDD RED was observed: focused collection failed with `ModuleNotFoundError` for the not-yet-created `agent_roles` module.
- Review regression RED was observed for live/order statuses, non-paper direct
  outcomes, secret/arbitrary task payloads, undeclared gateways, and optional
  task failures; the focused suite is green after the hardening patch.
- Residual-review RED was observed for integer paper flags, over-advertised
  tools, optional `None`/invalid/typed outcomes, non-finite numbers, nested
  paths, and unsafe failure/evidence fields; the full research suite is green
  after the final boundary patch.
- Identifier-review RED was observed for secret/path/URI content in roles,
  task IDs, evidence refs, failure kinds, and digests; `ssh://`, `s3://`,
  `~/`, and backslash paths are now rejected by the shared public grammar.

## Risks and unfinished items

- The runtime intentionally returns typed failure envelopes rather than
  retrying or persisting jobs; durable queue/worker behavior belongs to Task 5.
- Deterministic gateways are passed as opaque, allowlisted context values and
  are not serialized by the contracts. Their concrete risk/portfolio/paper
  implementations belong to Task 4.
- Task 2/3 files are maintained by their respective agents; Task 1 did not
  modify those files.
