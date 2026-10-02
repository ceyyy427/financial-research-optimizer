# Future Agent and MCP Readiness Audit

**Result:** ARCHITECTURALLY PREPARED; no agent or MCP research tools implemented

## Potential future architecture

```text
Research Agent -> capability-limited MCP tools -> Research Capability
```

| Future tool | Safe responsibility | Existing boundary it may call |
| --- | --- | --- |
| Data Tool | Load approved fixtures or invoke allowlisted providers and return provenance. | `data` package |
| Experiment Tool | Execute/reproduce an approved experiment and return a ResearchRun. | `experiments` package |
| Knowledge Tool | Query reviewed research-memory objects without changing historical evidence. | Future P6 adapter |
| Visualization Tool | Render data/result views without altering evidence or conclusions. | Read-only ResearchRun/result input |

## Readiness strengths

- Small domain modules are suitable for narrow tool wrappers.
- Structured JSON records and fingerprints provide auditable tool outputs.
- Agent role contracts already separate planning, implementation, review,
  research, security, dependency, and release responsibilities.
- Provider networking, local persistence, and research transformations have
  separate boundaries.

## Required controls before P7

- Explicit capability and read/write scopes per tool.
- Human approval for state-changing operations and all financial conclusions.
- Treat provider data, stored text, and graph content as untrusted input;
  prevent prompt-injection text from becoming tool instructions.
- No brokerage, live execution, secret exposure, shell escape, arbitrary URL,
  arbitrary path, pickle, or stored-code execution.
- Structured audit logs, deterministic fixtures, time/resource limits,
  reproducible tool versions, and independent adversarial evaluation.
- Evidence, evaluation, conclusion, and insight must remain distinct.

## Ollama and model-serving boundary

No Ollama package, import, configuration, or integration exists in the project.
The host has a pre-existing `/usr/local/bin/ollama` command, but this audit did
not install, invoke for inference, configure, or reference it from repository
code. Any future local-model integration requires its own dependency, privacy,
resource, evaluation, and security gate.

## Decision

The repository exposes reasonable future seams for governed tools, but P7 is
not authorized. Do not implement agents, MCP research tools, or model serving
in P4.5.
