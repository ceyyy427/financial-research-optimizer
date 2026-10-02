# P5.5 Skill and Capability Matrix

**Review date:** 2026-10-02  
**Starting commit:** `358ade94bd26d246e907414fc3ac729dc5ae1d5e`  
**Decision:** Use existing trusted skills and repository-native tooling; add no
plugin, MCP server, dependency, or external agent framework.

## Capability decisions

| Capability | Evidence inspected | Decision | Boundary |
|---|---|---|---|
| Planning / implementation | `superpowers:writing-plans`, `superpowers:executing-plans`, prior P5 plans | PRESENT / USE | This spec and plan are authoritative for the mission. |
| Brainstorming / scope | `superpowers:brainstorming`, user-supplied mission | PRESENT / USE | The supplied brief is treated as the approved design; no scope expansion. |
| TDD / verification | `superpowers:test-driven-development`, `superpowers:verification-before-completion` | PRESENT / USE | Red focused tests precede each new contract; full gates precede claims. |
| Quant validity | `financial-research-optimizer`, `linear-regression-analysis` | PRESENT / CONDITIONAL | Apply for PIT/OOS/leakage and regression interpretation; no library import. |
| Security / dependency review | repository `.agents/security-reviewer.md`, `.agents/dependency-manager.md`, P5 admission records | PRESENT / USE | Existing review controls are sufficient; inspect source and scans directly. |
| Code / architecture review | repository `.agents/reviewer.md`, `.agents/architect.md`, structured Git tools | PRESENT / USE | Independent passes A–G are required at gates. |
| Documentation | `superpowers:writing-plans`, repository Markdown conventions | PRESENT / USE | Required P5.5/P6 contracts and reports are versioned with code. |
| Data analytics / report skills | available data-analytics catalog | PRESENT / CONDITIONAL | No connected data source is in scope; deterministic fixtures are authoritative. |
| UI / visual design | UI and site skills are available | PRESENT / OUT-OF-SCOPE | P5.5/P6 deliver backend contracts and auditable workflow records, not UI. |
| Computer Use | CUA available | PRESENT / NOT NEEDED | No browser or desktop interaction is required by the repository task. |
| MCP | resource/template inventory returned no trusted quant runtime | ABSENT / NOT NEEDED | Keep the internal typed gateway authoritative and MCP-ready, not dependent. |
| Security plugin | Codex Security is only a recommended, uninstalled plugin | ABSENT / NOT NEEDED | Do not install; repository security review and adversarial tests cover scope. |
| New quant libraries | P5 admission matrix and isolated `.venv-quant` | DEFERRED | Keep only `statsmodels==0.15.0` in `.venv-quant`; all listed candidates remain deferred/reference. |

## Tool priority

Use `rg`, normal file tools, `apply_patch`, pytest, Ruff, Make targets, and the
existing governance script first. Use structured MCP/GitHub tools only when a
repository operation specifically needs them. External web search is not
needed for this offline implementation; if a time-sensitive external fact is
required, use only a primary source and record it as evidence rather than
allowing it to alter the quant contract.

## Non-install decision

No skill, plugin, MCP framework, quant library, model provider, data provider,
or orchestration framework is installed for this mission. This is deliberate:
there is no demonstrated capability gap, and adding one would weaken the
reproducibility and dependency-isolation gates. The matrix is an audit record,
not permission for arbitrary future installation.

