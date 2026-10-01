# Contributing

Contributions should improve reproducibility, source traceability, or the
clarity of the research. Read `ARCHITECTURE.md`, `DEPENDENCY_RECORD.md`, and
the applicable phase gate before changing code.

## Scope and safety

Keep network access inside provider modules, use allowlisted official sources,
and add a recorded fixture for deterministic tests. Do not add secrets,
trading automation, or investment advice. P4 experiment persistence remains
out of scope until a reviewed proposal changes the project state.

## Change workflow

1. Describe the research question or maintenance need and its evidence.
2. Add or update tests before implementation and run the focused test.
3. Record every dependency change in `DEPENDENCY_RECORD.md` and pin versions
   in `requirements.lock` when the environment exists.
4. Update the relevant architecture, evolution, or upgrade record.
5. Run `python scripts/validate_governance.py` and the complete test suite.
6. Ask an independent reviewer to check the phase gate and research
   limitations before merging.

Use clear commits and keep each change focused. A review should be able to
reproduce the result from a clean checkout without live network access.
