# P0 Gate Design

P0 establishes the repository contract that later phases must preserve.

## Entry criteria

- The P0–P3 scope and explicit P4 boundary are documented.
- The architecture separates providers, datasets, validation, features, and
  factors.
- Safety, dependency, evolution, and upgrade policies have named records.

## Checks

- Confirm every required governance document and role contract exists and is
  non-empty.
- Run `python scripts/validate_governance.py` from the repository root.
- Run the focused governance tests with the available test runner.
- Inspect that no governance check requires network access or third-party
  packages.
- Confirm `docs/PROJECT_STATE.md` records P0 as PASS and P4 as out of scope.

## Independent review

Review result: PASS

The reviewer checks the required file list, safety boundary, phase status,
dependency/evolution policies, and the validator's failure messages. Review
evidence is recorded in `docs/PROJECT_STATE.md` and `EVOLUTION_LOG.md`.

## Exit criteria

- The governance validator exits zero on a clean repository.
- Missing files and invalid phase state produce non-zero exits with actionable
  messages.
- The repository is ready for P1 environment work without changing the P0
  safety or review contract.

P0 gate status: PASS
