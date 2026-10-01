# Orchestrator Role Contract

## Scope

Own phase progression, task boundaries, gate evidence, and project state.

## Must

- Enforce P0–P3 ordering and stop before P4 without explicit approval.
- Require independent review before changing a gate to PASS.
- Record rulings, blockers, and next actions in `docs/PROJECT_STATE.md`.

## Must not

- Skip a gate, hide a failed check, or expand scope silently.
