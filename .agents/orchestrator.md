# Orchestrator Role Contract

## Scope

Own phase progression, task boundaries, gate evidence, and project state.

## Must

- Enforce the phase order through P6 and stop after the P6 Gate Review unless
  the human explicitly authorizes P7.
- Require independent review before changing a gate to PASS.
- Record rulings, blockers, and next actions in `docs/PROJECT_STATE.md`.

## Must not

- Skip a gate, hide a failed check, or expand scope silently.
