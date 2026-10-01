# Upgrade Proposal

Material dependency, architecture, data-source, or phase-scope changes start
as a proposal. A proposal is not an implementation instruction until an
independent review records a decision.

## Required contents

- Problem and evidence, including the affected phase gate.
- Proposed behavior and compatibility impact for callers, fixtures, and data.
- Security and research-quality implications, including leakage and
  provenance risks.
- Dependency changes with an entry in `DEPENDENCY_RECORD.md`.
- Migration, rollback, and validation plan.
- Reviewer, date, decision, and follow-up in `EVOLUTION_LOG.md`.

P4 experiment persistence and orchestration require an explicit approved
proposal; they are out of scope for the P0–P3 delivery.
