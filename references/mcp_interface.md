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

## Phase-one tools

| Tool | Input | Output |
|---|---|---|
| `create_research_run` | `task`, `mode`, `output_level`, optional `universe`, `target`, `horizon`, `constraints` | `run_id`, `plan_id`, accepted status and artifact base URI |
| `get_run_status` | `run_id` | lifecycle status, stage, progress, fallbacks, blocked nodes, completion level |
| `read_research_artifact` | `run_id`, logical artifact name | metadata, SHA-256, MIME type, and bounded text content |

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

The `mcp_run.schema.json` response schema covers accepted, status, blocked,
and artifact responses. The run directory stores `run.json`, `contract.json`,
`plan.json`, `status.json`, `execution.json`, `checkpoint.json`, and the
manifest; only manifest-registered output files are reader-facing resources.

## Boundary rule

Patchright/CDP, online providers, Python analysis, Plan DAG execution, and
provenance stay in the core engine. MCP is an adapter for an external agent;
it must not duplicate those rules or weaken `policy_guard`, preflight,
point-in-time, cost, risk, or artifact-lineage gates.
