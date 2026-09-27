# MCP interface contract

The MCP integration is an optional, thin external boundary. It does not
contain research logic and does not call individual handlers. Every request
is routed through `financial_research.runtime.run_research`, which builds the
immutable Research Contract, Plan DAG, checkpoint, provenance records, HTML
output, and decision table.

## Install and transports

```bash
python3 -m pip install -e '.[mcp]'
fro-mcp
fro-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

The HTTP transport is intended for a protected local or server network. Add
deployment authentication and network policy before exposing it beyond
localhost. The server does not accept credentials, arbitrary handler names,
arbitrary output directories, or arbitrary filesystem paths from tool calls.

## Lifecycle tools

| Tool | Input | Output |
|---|---|---|
| `create_research_run` | `task`, `mode`, `output_level`, optional scope, `idempotency_key`, `client_id`, `owner_id`, `tenant_id` | `run_id`, `plan_id`, accepted status, status URI and artifact base URI |
| `get_run_status` | `run_id`, client/owner/tenant identity | lifecycle status, stage, progress, lease, fallbacks, blocked nodes, completion level |
| `read_research_artifact` | `run_id`, logical artifact name, client/owner/tenant identity | metadata, SHA-256, MIME type, and bounded text content |
| `cancel_research_run` | `run_id`, client/owner/tenant identity | cancellation status; a terminal run is never rewritten |
| `resume_research_run` | `run_id`, client/owner/tenant identity | queued status and checkpoint-based restart |
| `retry_research_run` | `run_id`, client/owner/tenant identity | queued status for failed/blocked runs |
| `list_research_runs` | filters, cursor, client/owner/tenant identity | isolated status page and next cursor |

`mode` is one of `data_audit`, `descriptive_analysis`, `forecasting`,
`backtest`, and `portfolio_research`. `output_level` is one of `minimal`,
`standard`, `research_grade`, and `portfolio_grade`; backtests and portfolio
research cannot run below `research_grade`.

Errors are structured as `{status: "blocked", reason_code, message,
user_action_required}`. A blocked preflight or policy guard result is not a
successful forecast.

## Resources and artifact security

Registered artifacts are addressable as:

```text
research://runs/{run_id}/{artifact}
```

The URI parser accepts only a validated run ID and a simple artifact name.
The run store resolves the file below its operator-owned run directory and
checks the manifest, size limit, MIME type, and SHA-256 before returning it.
Aliases include `contract`, `plan`, `status`, `manifest`, `analysis`,
`preflight`, `report_html`, and `decision_table`. An MCP caller cannot read
`/etc/passwd`, `../../secret`, or an unregistered file by passing a path.

The `mcp_run.schema.json` envelope plus `agent_contracts/mcp_run_request.schema.json`,
`agent_contracts/mcp_run_status.schema.json`, and
`agent_contracts/mcp_tool_result.schema.json` cover accepted, status, blocked,
and artifact responses. The run directory stores `run.json`, `contract.json`,
`plan.json`, `status.json`, `execution.json`, `checkpoint.json`, and the
manifest; only manifest-registered output files are reader-facing resources.

The default JSON backend uses atomic `fsync` + replace writes and a cross-process
`flock`/marker lock. Set `FRO_RUN_STORE=sqlite` to use the SQLite metadata backend
(WAL and busy timeout) while retaining bounded artifact files. `FRO_MCP_RUN_ROOT`
selects the run root. The store persists request hashes, idempotency keys, owner and
tenant identity, attempts, durable leases, heartbeats, stale-lease recovery, event
records, and checkpoint fingerprints. A key reused with different request content is
an explicit `idempotency_conflict`; it never silently creates a second run.

## Boundary rule

Patchright/CDP, online providers, Python analysis, Plan DAG execution, and
provenance stay in the core engine. MCP is an adapter for an external agent;
it must not duplicate those rules or weaken `policy_guard`, preflight,
point-in-time, cost, risk, or artifact-lineage gates.
