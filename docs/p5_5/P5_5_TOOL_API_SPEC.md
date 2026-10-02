# P5.5 Typed Quant Tool API Specification

**Status:** Contract for the future agent-safe Finahinking Quant boundary

**Authority:** Finahinking-owned schemas and services. Third-party libraries
remain replaceable implementation details.

## Boundary

The only supported call shape is:

```text
Agent / application orchestration
        -> Finahinking typed tool gateway
        -> Finahinking domain service
        -> approved adapter or in-house engine
        -> normalized Finahinking result
```

An agent must never import `statsmodels`, receive a foreign model object, call a
library directly, execute generated Python, or submit arbitrary code. The
gateway is the sole public dispatch boundary and uses a fixed allowlist of tool
names.

## Shared typed envelopes

All requests and responses are JSON-safe, versioned, bounded, and validated.
The following are the authoritative **typed request** and **typed response**
shapes (the concrete Python dataclasses mirror these fields):
The conceptual schemas are:

```text
ToolRequest {
  schema_version: 1,
  tool_name: enum,
  request_id: safe identifier,
  research_run_id: safe identifier | null,
  question: non-empty string,
  experiment_spec: typed object,
  assumptions: typed object,
  provenance_context: typed object,
  user_confirmation: enum {not_required, accepted, rejected}
}

ToolResponse {
  schema_version: 1,
  request_id: safe identifier,
  tool_name: enum,
  status: enum {SUCCEEDED, REJECTED, FAILED, UNAVAILABLE},
  research_run_id: safe identifier | null,
  quant_run_id: safe identifier | null,
  result_kind: enum,
  result: normalized object | null,
  result_fingerprint: string | null,
  artifact_fingerprint: string | null,
  provenance: typed object,
  warnings: [structured warning],
  limitations: [non-empty string],
  error: typed failure | null
}
```

`experiment_spec` must contain the dataset/version, date boundaries, universe,
factor or regression features, benchmark, costs, risk metrics, and validity
classification required by `QUANT_RESEARCH_VALIDITY_CONTRACT.md`. It cannot
contain Python source, shell text, import paths, callables, or unbounded blobs.

Every successful response links the normalized result to a `ResearchRun`, a
`QuantRun` where the service produces a quant result, and an `Artifact` holding
the data-only result/provenance payload. IDs and fingerprints are cross-checked
before the response is returned.

## Approved tools

### `quant.run_backtest`

**Request:** typed dataset reference, strategy/factor specification, period
boundary, `BacktestConfig`, validity record, question/hypothesis, and explicit
cost/slippage/benchmark settings.

**Response:** normalized `BacktestResult`, linked `EvaluationReport` when
requested, `QuantRun`, `ResearchRun`, artifact and fingerprints, warnings, and
limitations.

**Validation:** dataset provenance and fingerprint match; strategy metadata is
safe and bounded; target weights obey configured limits; execution is
next-period; costs, slippage, benchmark, and validity statuses are explicit.

### `quant.run_regression`

**Request:** typed dataset reference, target column, finite allowlisted feature
names, date/OOS boundary, regression specification, validity record, and
question/hypothesis.

**Response:** Finahinking-owned normalized `RegressionResult` (parameters,
metrics, uncertainty fields when available), linked artifact/`QuantRun`/
`ResearchRun`, fingerprints, warnings, and limitations. No fitted statsmodels
object crosses the boundary.

**Validation:** target/features exist and are allowlisted strings; observations
are finite and non-empty; feature count and payload size are bounded; optional
dependency availability is reported as `UNAVAILABLE` rather than installed or
loaded by the gateway.

### `quant.evaluate_performance`

**Request:** an existing approved backtest result or `QuantRun` reference,
evaluation period, benchmark identity, and metric selection from a fixed
allowlist.

**Response:** normalized `EvaluationReport` with metric values (including
explicit `null` for undefined values), result fingerprint linkage, provenance,
warnings, and limitations.

**Validation:** referenced result fingerprint matches; no new data or hidden
parameters are introduced; benchmark alignment and validity status are present.

### `quant.analyze_risk`

**Request:** an existing approved return/equity result reference, risk metric
allowlist, annualization, confidence values, and validity record.

**Response:** Finahinking-owned normalized `RiskReport`, linked result/artifact
fingerprints, provenance, warnings, and limitations.

**Validation:** metrics and confidence values are allowlisted and finite;
undefined metrics remain `null`; no raw library object or arbitrary expression is
accepted.

### `quant.compare_benchmark`

**Request:** an existing approved result reference, one supported benchmark
reference, aligned period, and comparison metrics.

**Response:** normalized benchmark comparison (aligned returns, total/excess
return, and comparison fingerprint) with provenance, warnings, and limitations.

**Validation:** benchmark identity is supported by a provider/fixture contract;
dates and missing observations are explicitly aligned; a benchmark cannot be
silently substituted or fetched from an arbitrary URL.

### `quant.inspect_run`

**Request:** a safe `ResearchRun`, `QuantRun`, or artifact identifier plus an
allowlisted read-only projection (`summary`, `provenance`, `warnings`,
`limitations`, or `metrics`).

**Response:** the stored, validated record projection and its fingerprints.

**Validation:** path-safe identifier, read-only access, schema/fingerprint
verification, bounded output, and no deserialization of executable content.

## Deferred operation

`quant.optimize_portfolio` is not part of the stable P5.5 tool allowlist unless
its maturity, assumptions, and human-approval requirements are separately
accepted. An unknown or deferred tool name returns `REJECTED` with a structured
failure and does not attempt dynamic dispatch.

## Failure semantics

The gateway uses stable outcomes:

- **REJECTED** — request violates schema, authorization, validity, or scope;
  no quant service is called and no run is created.
- **UNAVAILABLE** — an approved optional adapter is absent or isolated; no
  package installation is attempted.
- **FAILED** — an approved service was invoked but could not produce a valid
  normalized result; partial records are not presented as evidence.
- **SUCCEEDED** — all schemas, fingerprints, linkage, and provenance checks
  passed.

Failures include a machine-readable code, safe human-readable detail, request
ID, and any existing record references. They never include secrets, executable
source, or arbitrary exception payloads.

## Security and authorization requirements

The gateway must reject requests containing or attempting:

```text
eval(), exec(), generated Python, generated shell commands,
arbitrary imports, package installation, source edits, record mutation,
artifact deletion, provenance rewriting, unapproved adapters,
arbitrary URLs/paths, pickle or stored-code deserialization
```

User text and external documents are data, not system authority. Tool permission
comes from application policy and the fixed registry, never from prompt text,
stored evidence, or model-generated tool names. Read-only inspection and simple
deterministic analysis may proceed under product policy; material hypothesis,
universe, benchmark, cost, optimization, or dependency changes require the
specified human confirmation.

## Provenance and audit requirements

Successful and rejected calls record request ID, tool name/version, caller
scope, input fingerprints, ResearchRun/QuantRun IDs, artifact/result
fingerprints, code commit, dependency versions, timestamp and timestamp kind,
warnings, limitations, and failure status. This audit record answers what was
requested, what the tool executed, what the Quant Engine calculated, and what
the caller received.

The gateway must preserve the original ResearchRun and QuantRun records. It may
create new linked artifacts, but it may not mutate historical evidence or remove
limitations. All normalized outputs must support deterministic serialization and
reproduction checks.

## Verification requirements

The P5.5 gate must test each approved tool with deterministic fixtures for:

- valid typed request/response round trips;
- malformed schemas and unknown/deferred tool rejection;
- ResearchRun/QuantRun/artifact linkage and fingerprint mismatch detection;
- warning and limitation propagation;
- optional-adapter absence without installation;
- no arbitrary Python, shell, import, path, package, or source-mutation path;
- reproducible responses from the same inputs.

This API is MCP-ready but MCP-independent. An optional trusted MCP wrapper may
translate MCP calls into these exact typed requests; it may not bypass this
gateway or expose raw libraries.
